import pytest

from sovereignty_figures.architecture import ArchitectureConfig


@pytest.mark.parametrize(
    "arch, ok, msg",
    [
        (ArchitectureConfig(sealed=True), False, "no exhaust path"),
        (ArchitectureConfig(sealed=True, exhaust_paths=["nozzle"]), False, "contradicts"),
        (ArchitectureConfig(sealed=False), False, "no exhaust path"),
        (ArchitectureConfig(sealed=False, exhaust_paths=["nozzle"]), True, None),
        (ArchitectureConfig(sealed=False, exhaust_paths=["nozle"]), False, "Unknown exhaust path"),
    ],
)
def test_architecture_matrix(arch, ok, msg):
    if ok:
        assert arch.is_open_momentum_path() is True
        arch.validate_architecture()
    else:
        assert arch.is_open_momentum_path() is False
        with pytest.raises(ValueError, match=msg):
            arch.validate_architecture()
