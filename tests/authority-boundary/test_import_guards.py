from pathlib import Path


FORBIDDEN_IMPORTS = {
    "scar_ledger",
    "storage",
    "transport",
    "evidence",
    "identity",
}


def test_orchestrator_source_has_no_authority_layer_imports():
    source = Path("crates/orchestrator/src/router.rs").read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_IMPORTS:
        assert forbidden not in source


def test_orchestrator_does_not_define_authorization():
    source = Path("crates/orchestrator/src/router.rs").read_text(encoding="utf-8")
    assert "authorize(" not in source
    assert "grant" not in source.lower()
