"""Security regression tests for scripts/oauth_local_generator.py."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "oauth_local_generator.py"
spec = importlib.util.spec_from_file_location("oauth_local_generator", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def run_generator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


class TestDeterministicKeyIds:
    def test_same_public_key_has_same_kid(self) -> None:
        public_key = bytes(range(32))
        assert module.derive_kid(public_key) == module.derive_kid(public_key)

    def test_kid_is_sha256_prefix(self) -> None:
        public_key = b"public-key".ljust(32, b"!")
        assert module.derive_kid(public_key) == hashlib.sha256(public_key).hexdigest()[:32]

    def test_different_public_keys_have_different_kids(self) -> None:
        assert module.derive_kid(b"a" * 32) != module.derive_kid(b"b" * 32)


@pytest.mark.skipif(platform.system() == "Windows", reason="POSIX permissions unavailable")
class TestRestrictivePermissions:
    def test_generated_files_and_directory_are_private(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "credentials"
        result = run_generator("--output-dir", str(output_dir))
        assert result.returncode == 0, result.stderr

        assert mode(output_dir) == 0o700
        for filename in ("oauth-client.json", module.PRIVATE_KEY_FILENAME, "provenance.json"):
            assert mode(output_dir / filename) == 0o600


class TestExclusiveFileCreation:
    def test_json_writer_does_not_overwrite_existing_content(self, tmp_path: Path) -> None:
        path = tmp_path / "credentials.json"
        path.write_text("original\n", encoding="utf-8")

        with pytest.raises(FileExistsError):
            module.write_json_exclusive(path, {"replacement": True}, 0o600)

        assert path.read_text(encoding="utf-8") == "original\n"

    def test_pem_writer_does_not_overwrite_existing_content(self, tmp_path: Path) -> None:
        path = tmp_path / "signing.pem"
        path.write_bytes(b"original")

        with pytest.raises(FileExistsError):
            module.write_pem_exclusive(path, b"replacement", 0o600)

        assert path.read_bytes() == b"original"

    def test_generation_does_not_write_partial_artifacts_when_directory_exists(
        self, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "credentials"
        output_dir.mkdir()
        sentinel = output_dir / "sentinel"
        sentinel.write_text("keep", encoding="utf-8")

        result = run_generator("--output-dir", str(output_dir))
        assert result.returncode == 1
        assert sentinel.read_text(encoding="utf-8") == "keep"
        assert sorted(path.name for path in output_dir.iterdir()) == ["sentinel"]


class TestReportContents:
    def test_dry_run_report_is_local_and_skips_generation(self) -> None:
        result = run_generator("--service", "test-service", "--dry-run")
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)

        assert report["service"] == "test-service"
        assert report["issuer"] == "local"
        assert report["signing_algorithm"] == "Ed25519"
        assert report["network_accessed"] is False
        assert report["validation"] == "PASS"
        assert report["generation"] == "SKIPPED"
        assert report["persistence"] == "SKIPPED"
        assert report["dry_run"] is True

    def test_generation_report_matches_artifacts(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "credentials"
        result = run_generator(
            "--service",
            "test-service",
            "--output-dir",
            str(output_dir),
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        metadata = json.loads((output_dir / "oauth-client.json").read_text(encoding="utf-8"))
        provenance = json.loads((output_dir / "provenance.json").read_text(encoding="utf-8"))

        assert report["service"] == "test-service"
        assert report["issuer"] == "local"
        assert report["signing_algorithm"] == "Ed25519"
        assert report["network_accessed"] is False
        assert report["validation"] == "PASS"
        assert report["generation"] == "PASS"
        assert report["persistence"] == "PASS"
        assert report["output_dir"] == str(output_dir.resolve())
        assert report["provenance_file"] == str((output_dir / "provenance.json").resolve())
        assert report["kid"] == metadata["kid"] == provenance["kid"]

    def test_report_file_contains_same_schema(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "credentials"
        report_path = tmp_path / "reports" / "generation.json"
        result = run_generator(
            "--dry-run",
            "--service",
            "test-service",
            "--report",
            str(report_path),
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(report_path.read_text(encoding="utf-8"))

        assert report["service"] == "test-service"
        assert report["issuer"] == "local"
        assert report["network_accessed"] is False
        assert report["validation"] == "PASS"
        assert not output_dir.exists()
