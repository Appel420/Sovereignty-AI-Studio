from pathlib import Path

from backend.coordination.sghv119_maintenance import run_maintenance


def _copy_contract_surface(tmp_path: Path) -> Path:
    files = {
        "docs/architecture/SGHV119_RUNTIME.md": "DECLARED CONFIGURED AVAILABLE VERIFIED ACTIVE UNAVAILABLE DENY REQUIRE_APPROVAL local/offline mode",
        "frontend/runtime/transport.js": "export const transport = {};",
        "scripts/run-local-ci.py": "print('local')",
        "backend/coordination/execution_contracts.py": "class RouteDecision: pass",
        "backend/coordination/devassist_adapter.py": '"""does not authorize"""\nif route.decision != "ALLOW":\n    raise PermissionError\nif route.route not in self._allowed_routes:\n    raise PermissionError\n',
        "backend/coordination/task_envelope.py": "class TaskEnvelope: pass",
        "config/ci-mode-registry.json": "{}",
        "integration/repository-registry.json": "{}",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def test_maintenance_passes_without_mutating_repository(tmp_path):
    root = _copy_contract_surface(tmp_path)
    before = sorted(str(path.relative_to(root)) for path in root.rglob("*"))

    result = run_maintenance(root)

    after = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    assert result["status"] == "PASS"
    assert result["mode"] == "offline-read-only"
    assert result["network"] == "disabled-by-design"
    assert result["authorization"] == "not-granted-by-runner"
    assert before == after


def test_missing_contract_fails_closed(tmp_path):
    root = _copy_contract_surface(tmp_path)
    (root / "docs/architecture/SGHV119_RUNTIME.md").unlink()

    result = run_maintenance(root)

    assert result["status"] == "FAIL"
    assert result["admissible"] is False
    assert any(not check["passed"] for check in result["checks"])


def test_missing_devassist_boundary_fails_closed(tmp_path):
    root = _copy_contract_surface(tmp_path)
    (root / "backend/coordination/devassist_adapter.py").write_text(
        "class UnsafeAdapter: pass\n", encoding="utf-8"
    )

    result = run_maintenance(root)

    assert result["status"] == "FAIL"
    assert result["admissible"] is False
