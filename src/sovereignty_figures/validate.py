from __future__ import annotations


def validate_thrust(P_watts: float, eta: float, Isp_s: float, tol: float = 1e-9) -> float:
    """Validate thrust inputs and return idealized thrust in newtons.

    Uses F = 2 * eta * P / (Isp * g0).
    """
    if P_watts <= 0:
        raise ValueError("P_watts must be > 0")
    if not 0 < eta < 1:
        raise ValueError("eta must satisfy 0 < eta < 1")
    if Isp_s <= 0:
        raise ValueError("Isp_s must be > 0")
    if tol < 0:
        raise ValueError("tol must be >= 0")
    return 2.0 * eta * P_watts / (Isp_s * 9.80665)
