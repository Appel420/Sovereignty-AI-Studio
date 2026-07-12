"""Tests for scripts/oauth_local_generator.py.

Covers:
- validate_service: valid and invalid patterns
- canonicalize_config: stable output
- derive_kid: deterministic from public key
- policy_gate: approved algorithm and issuer enforcement
- create_provenance: required fields and UTC timestamp format
- canonical_json: sorted keys, deterministic output
- generate_key_material: key structure and kid derivation
- dry-run: no credential artifacts written, correct report fields
- full generation: separate private-key file, no private key in metadata
- PKCS#8 PEM format: loadable by standard cryptography tooling
- permissions: oauth-client.json and oauth-private-key.pem are mode 0600
- no-overwrite: FileExistsError on directory or file collision
- provenance.json: written to output directory with required fields
- failure/partial-write: existing directory returns persistence FAIL without crash
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Import the module under test by file path so tests don't require the scripts/
# directory to be on sys.path (matching the pattern used in test_local_control_plane.py).
import importlib.util

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "oauth_local_generator.py"
_spec = importlib.util.spec_from_file_location("oauth_local_generator", _SCRIPT_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

b64url = _mod.b64url
canonical_json = _mod.canonical_json
canonicalize_config = _mod.canonicalize_config
create_provenance = _mod.create_provenance
derive_kid = _mod.derive_kid
generate_key_material = _mod.generate_key_material
persist_artifacts = _mod.persist_artifacts
policy_gate = _mod.policy_gate
validate_service = _mod.validate_service
write_json_exclusive = _mod.write_json_exclusive
write_pem_exclusive = _mod.write_pem_exclusive
TOOL_VERSION = _mod.TOOL_VERSION
PRIVATE_KEY_FILENAME = _mod.PRIVATE_KEY_FILENAME

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_script(*args: str) -> subprocess.CompletedProcess:
    """Run the generator script as a subprocess and return the result."""
    return subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
    )


def _file_mode(path: Path) -> int:
    """Return the permission bits (e.g. 0o600) for *path*."""
    return stat.S_IMODE(path.stat().st_mode)


# ---------------------------------------------------------------------------
# Phase 1 – validate_service
# ---------------------------------------------------------------------------


class TestValidateService:
    def test_valid_default(self):
        validate_service("sovereignty-ai-studio")  # must not raise

    def test_valid_simple(self):
        validate_service("myservice")

    def test_valid_with_digits(self):
        validate_service("svc123")

    def test_valid_with_underscore(self):
        validate_service("my_service")

    def test_valid_with_hyphen(self):
        validate_service("my-service")

    def test_invalid_uppercase(self):
        with pytest.raises(ValueError, match="service must contain"):
            validate_service("MyService")

    def test_invalid_leading_hyphen(self):
        with pytest.raises(ValueError, match="service must contain"):
            validate_service("-bad")

    def test_invalid_space(self):
        with pytest.raises(ValueError, match="service must contain"):
            validate_service("bad service")

    def test_invalid_empty(self):
        with pytest.raises(ValueError, match="service must contain"):
            validate_service("")

    def test_invalid_too_long(self):
        with pytest.raises(ValueError, match="service must contain"):
            validate_service("a" * 65)

    def test_invalid_special_chars(self):
        with pytest.raises(ValueError, match="service must contain"):
            validate_service("bad@name")


# ---------------------------------------------------------------------------
# Phase 2 – canonicalize_config
# ---------------------------------------------------------------------------


class TestCanonicalizeConfig:
    def test_returns_expected_keys(self):
        cfg = canonicalize_config("testsvc")
        assert cfg["issuer"] == "local"
        assert cfg["service"] == "testsvc"
        assert cfg["signing_algorithm"] == "Ed25519"
        assert cfg["tool_version"] == TOOL_VERSION

    def test_deterministic(self):
        assert canonicalize_config("svc") == canonicalize_config("svc")

    def test_different_services_differ(self):
        assert canonicalize_config("svc-a")["service"] != canonicalize_config("svc-b")["service"]


# ---------------------------------------------------------------------------
# derive_kid – deterministic key identifier
# ---------------------------------------------------------------------------


class TestDeriveKid:
    def test_deterministic_from_same_bytes(self):
        pub = b"\x01" * 32
        assert derive_kid(pub) == derive_kid(pub)

    def test_different_keys_produce_different_kids(self):
        pub_a = b"\x01" * 32
        pub_b = b"\x02" * 32
        assert derive_kid(pub_a) != derive_kid(pub_b)

    def test_kid_is_hex_lowercase(self):
        kid = derive_kid(b"\xab\xcd" * 16)
        assert kid == kid.lower()
        int(kid, 16)  # must be valid hex

    def test_kid_is_32_chars(self):
        kid = derive_kid(b"\x00" * 32)
        assert len(kid) == 32

    def test_kid_matches_sha256_prefix(self):
        pub = b"\xde\xad\xbe\xef" * 8
        expected = hashlib.sha256(pub).hexdigest()[:32]
        assert derive_kid(pub) == expected

    def test_kid_is_reproducible_from_real_key(self):
        private_key = Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        kid1 = derive_kid(pub_bytes)
        kid2 = derive_kid(pub_bytes)
        assert kid1 == kid2


# ---------------------------------------------------------------------------
# Phase 4 – policy_gate
# ---------------------------------------------------------------------------


class TestPolicyGate:
    def test_valid_config_passes(self):
        policy_gate({"issuer": "local", "signing_algorithm": "Ed25519"})

    def test_rejects_unknown_algorithm(self):
        with pytest.raises(ValueError, match="signing_algorithm"):
            policy_gate({"issuer": "local", "signing_algorithm": "RSA"})

    def test_rejects_network_issuer(self):
        with pytest.raises(ValueError, match="issuer must be 'local'"):
            policy_gate({"issuer": "remote", "signing_algorithm": "Ed25519"})


# ---------------------------------------------------------------------------
# Phase 5 – create_provenance
# ---------------------------------------------------------------------------


class TestCreateProvenance:
    def test_required_fields_present(self):
        p = create_provenance("testsvc", "deadbeef" * 4)
        for key in ("algorithm", "event", "kid", "service", "timestamp", "tool_version"):
            assert key in p, f"missing key: {key}"

    def test_event_is_credential_generated(self):
        p = create_provenance("s", "k")
        assert p["event"] == "credential_generated"

    def test_algorithm_is_ed25519(self):
        p = create_provenance("s", "k")
        assert p["algorithm"] == "Ed25519"

    def test_timestamp_is_utc_iso8601(self):
        import re
        p = create_provenance("s", "k")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", p["timestamp"])

    def test_tool_version_matches_module(self):
        p = create_provenance("s", "k")
        assert p["tool_version"] == TOOL_VERSION


# ---------------------------------------------------------------------------
# canonical_json – deterministic serialization
# ---------------------------------------------------------------------------


class TestCanonicalJson:
    def test_keys_are_sorted(self):
        text = canonical_json({"z": 1, "a": 2, "m": 3})
        data = json.loads(text)
        assert list(data.keys()) == sorted(data.keys())

    def test_output_is_deterministic(self):
        value = {"b": [1, 2], "a": "hello"}
        assert canonical_json(value) == canonical_json(value)

    def test_ends_with_newline(self):
        assert canonical_json({}) .endswith("\n")

    def test_nested_keys_sorted(self):
        text = canonical_json({"outer": {"z": 1, "a": 2}})
        obj = json.loads(text)
        assert list(obj["outer"].keys()) == ["a", "z"]

    def test_two_spaces_indent(self):
        text = canonical_json({"k": "v"})
        assert '  "k": "v"' in text


# ---------------------------------------------------------------------------
# generate_key_material
# ---------------------------------------------------------------------------


class TestGenerateKeyMaterial:
    def test_returns_four_elements(self):
        result = generate_key_material()
        assert len(result) == 4

    def test_public_key_bytes_length(self):
        _, pub, _, _ = generate_key_material()
        assert len(pub) == 32

    def test_kid_is_32_char_hex(self):
        _, _, kid, _ = generate_key_material()
        assert len(kid) == 32
        int(kid, 16)

    def test_client_id_starts_with_sg(self):
        _, _, _, cid = generate_key_material()
        assert cid.startswith("sg_")

    def test_kid_matches_derive_kid(self):
        _, pub, kid, _ = generate_key_material()
        assert kid == derive_kid(pub)

    def test_consecutive_calls_produce_different_kids(self):
        _, _, kid1, _ = generate_key_material()
        _, _, kid2, _ = generate_key_material()
        assert kid1 != kid2


# ---------------------------------------------------------------------------
# dry-run behavior
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_exits_zero(self):
        result = _run_script("--dry-run")
        assert result.returncode == 0, result.stderr

    def test_dry_run_report_validation_pass(self):
        result = _run_script("--dry-run")
        data = json.loads(result.stdout)
        assert data["validation"] == "PASS"

    def test_dry_run_report_generation_skipped(self):
        result = _run_script("--dry-run")
        data = json.loads(result.stdout)
        assert data["generation"] == "SKIPPED"

    def test_dry_run_report_persistence_skipped(self):
        result = _run_script("--dry-run")
        data = json.loads(result.stdout)
        assert data["persistence"] == "SKIPPED"

    def test_dry_run_writes_no_credential_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            _run_script("--dry-run", "--report", str(report_path))
            files = list(Path(tmpdir).iterdir())
            # Only the report file should exist; no oauth-client.json etc.
            assert all(f.name == "report.json" for f in files)

    def test_dry_run_report_has_dry_run_flag(self):
        result = _run_script("--dry-run")
        data = json.loads(result.stdout)
        assert data.get("dry_run") is True

    def test_dry_run_no_output_dir_required(self):
        result = _run_script("--dry-run")
        assert result.returncode == 0

    def test_dry_run_network_accessed_false(self):
        result = _run_script("--dry-run")
        data = json.loads(result.stdout)
        assert data["network_accessed"] is False


# ---------------------------------------------------------------------------
# Full generation – artifact layout and content
# ---------------------------------------------------------------------------


class TestFullGeneration:
    def _generate(self, tmpdir: str, service: str = "test-svc") -> Path:
        out = Path(tmpdir) / "creds"
        result = _run_script("--service", service, "--output-dir", str(out))
        assert result.returncode == 0, result.stderr
        return out

    def test_oauth_client_json_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            assert (out / "oauth-client.json").exists()

    def test_private_key_pem_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            assert (out / PRIVATE_KEY_FILENAME).exists()

    def test_provenance_json_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            assert (out / "provenance.json").exists()

    def test_oauth_client_json_has_no_private_key_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            data = json.loads((out / "oauth-client.json").read_text())
            assert "private_key" not in data

    def test_oauth_client_json_has_key_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            data = json.loads((out / "oauth-client.json").read_text())
            assert data["key_reference"] == PRIVATE_KEY_FILENAME

    def test_oauth_client_json_has_kid(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            data = json.loads((out / "oauth-client.json").read_text())
            assert "kid" in data
            assert len(data["kid"]) == 32

    def test_oauth_client_json_kid_matches_jwks_kid(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            data = json.loads((out / "oauth-client.json").read_text())
            jwk = data["jwks"]["keys"][0]
            assert data["kid"] == jwk["kid"]

    def test_jwks_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            data = json.loads((out / "oauth-client.json").read_text())
            key = data["jwks"]["keys"][0]
            assert key["kty"] == "OKP"
            assert key["crv"] == "Ed25519"
            assert key["alg"] == "EdDSA"
            assert key["use"] == "sig"
            assert "x" in key

    def test_report_validation_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            result = _run_script("--output-dir", str(out))
            data = json.loads(result.stdout)
            assert data["validation"] == "PASS"

    def test_report_generation_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            result = _run_script("--output-dir", str(out))
            data = json.loads(result.stdout)
            assert data["generation"] == "PASS"

    def test_report_persistence_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            result = _run_script("--output-dir", str(out))
            data = json.loads(result.stdout)
            assert data["persistence"] == "PASS"

    def test_report_network_accessed_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            result = _run_script("--output-dir", str(out))
            data = json.loads(result.stdout)
            assert data["network_accessed"] is False

    def test_report_kid_matches_metadata_kid(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            result = _run_script("--output-dir", str(out))
            report = json.loads(result.stdout)
            metadata = json.loads((out / "oauth-client.json").read_text())
            assert report["kid"] == metadata["kid"]


# ---------------------------------------------------------------------------
# PKCS#8 PEM private key format
# ---------------------------------------------------------------------------


class TestPrivateKeyFormat:
    def _get_pem_bytes(self, tmpdir: str) -> bytes:
        out = Path(tmpdir) / "creds"
        result = _run_script("--output-dir", str(out))
        assert result.returncode == 0, result.stderr
        return (out / PRIVATE_KEY_FILENAME).read_bytes()

    def test_pem_starts_with_pkcs8_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            pem = self._get_pem_bytes(tmp)
            assert pem.startswith(b"-----BEGIN PRIVATE KEY-----")

    def test_pem_ends_with_pkcs8_footer(self):
        with tempfile.TemporaryDirectory() as tmp:
            pem = self._get_pem_bytes(tmp)
            assert b"-----END PRIVATE KEY-----" in pem

    def test_pem_is_loadable_by_cryptography(self):
        with tempfile.TemporaryDirectory() as tmp:
            pem = self._get_pem_bytes(tmp)
            key = serialization.load_pem_private_key(pem, None)
            assert isinstance(key, Ed25519PrivateKey)

    def test_pem_public_key_matches_jwks_x(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            _run_script("--output-dir", str(out))
            pem = (out / PRIVATE_KEY_FILENAME).read_bytes()
            metadata = json.loads((out / "oauth-client.json").read_text())
            key = serialization.load_pem_private_key(pem, None)
            pub_bytes = key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            assert b64url(pub_bytes) == metadata["jwks"]["keys"][0]["x"]


# ---------------------------------------------------------------------------
# File permissions (skipped on Windows where POSIX mode bits don't apply)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(platform.system() == "Windows", reason="POSIX permissions not applicable")
class TestFilePermissions:
    def _generate(self, tmpdir: str) -> Path:
        out = Path(tmpdir) / "creds"
        result = _run_script("--output-dir", str(out))
        assert result.returncode == 0, result.stderr
        return out

    def test_output_dir_is_mode_700(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            assert _file_mode(out) == 0o700

    def test_oauth_client_json_is_mode_600(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            assert _file_mode(out / "oauth-client.json") == 0o600

    def test_private_key_pem_is_mode_600(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            assert _file_mode(out / PRIVATE_KEY_FILENAME) == 0o600

    def test_provenance_json_is_mode_600(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate(tmp)
            assert _file_mode(out / "provenance.json") == 0o600


# ---------------------------------------------------------------------------
# No-overwrite behavior
# ---------------------------------------------------------------------------


class TestNoOverwrite:
    def test_existing_output_dir_returns_persistence_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            out.mkdir()
            result = _run_script("--output-dir", str(out))
            assert result.returncode == 1
            data = json.loads(result.stdout)
            assert data["persistence"] == "FAIL"
            assert "persistence_error" in data

    def test_existing_output_dir_writes_no_partial_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            out.mkdir()
            _run_script("--output-dir", str(out))
            # The pre-existing directory should contain no files written by the script.
            assert list(out.iterdir()) == []

    def test_write_json_exclusive_raises_on_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            write_json_exclusive(path, {"k": "v"}, 0o600)
            with pytest.raises(FileExistsError, match="already exists"):
                write_json_exclusive(path, {"k": "v2"}, 0o600)

    def test_write_pem_exclusive_raises_on_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "key.pem"
            write_pem_exclusive(path, b"data", 0o600)
            with pytest.raises(FileExistsError, match="already exists"):
                write_pem_exclusive(path, b"data2", 0o600)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_provenance_json_has_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            _run_script("--output-dir", str(out))
            p = json.loads((out / "provenance.json").read_text())
            for key in ("algorithm", "event", "kid", "service", "timestamp", "tool_version"):
                assert key in p, f"missing key: {key}"

    def test_provenance_event_is_credential_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            _run_script("--output-dir", str(out))
            p = json.loads((out / "provenance.json").read_text())
            assert p["event"] == "credential_generated"

    def test_provenance_timestamp_is_utc_iso8601(self):
        import re
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            _run_script("--output-dir", str(out))
            p = json.loads((out / "provenance.json").read_text())
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", p["timestamp"])

    def test_provenance_kid_matches_metadata_kid(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            _run_script("--output-dir", str(out))
            p = json.loads((out / "provenance.json").read_text())
            m = json.loads((out / "oauth-client.json").read_text())
            assert p["kid"] == m["kid"]

    def test_provenance_service_matches_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            _run_script("--service", "my-svc", "--output-dir", str(out))
            p = json.loads((out / "provenance.json").read_text())
            assert p["service"] == "my-svc"

    def test_report_references_provenance_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            result = _run_script("--output-dir", str(out))
            data = json.loads(result.stdout)
            assert "provenance_file" in data


# ---------------------------------------------------------------------------
# Deterministic JSON output
# ---------------------------------------------------------------------------


class TestDeterministicJSON:
    def test_oauth_client_json_keys_are_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            _run_script("--output-dir", str(out))
            text = (out / "oauth-client.json").read_text()
            data = json.loads(text)
            assert list(data.keys()) == sorted(data.keys())

    def test_provenance_json_keys_are_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "creds"
            _run_script("--output-dir", str(out))
            text = (out / "provenance.json").read_text()
            data = json.loads(text)
            assert list(data.keys()) == sorted(data.keys())

    def test_canonical_json_two_calls_identical(self):
        value = {"z": [3, 2, 1], "a": {"nested": True}, "m": 42}
        assert canonical_json(value) == canonical_json(value)


# ---------------------------------------------------------------------------
# Service name validation via CLI
# ---------------------------------------------------------------------------


class TestCLIValidation:
    def test_invalid_service_exits_nonzero(self):
        result = _run_script("--service", "Bad Service", "--dry-run")
        assert result.returncode != 0

    def test_missing_output_dir_without_dry_run_exits_nonzero(self):
        result = _run_script("--service", "testsvc")
        assert result.returncode != 0

    def test_default_service_dry_run_succeeds(self):
        result = _run_script("--dry-run")
        assert result.returncode == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
