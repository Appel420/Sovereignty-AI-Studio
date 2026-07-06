from __future__ import annotations

from loop_guard import LoopGuard


def test_continue_for_unique_output() -> None:
    guard = LoopGuard()

    result = guard.check("fix drift", "We should make one concrete next step.")

    assert result["action"] == "continue"
    assert result["reason"] == "unique_enough"


def test_breaks_on_exact_repeat() -> None:
    guard = LoopGuard()
    user = "fix drift"
    output = "We should make one concrete next step."

    assert guard.check(user, output)["action"] == "continue"
    result = guard.check(user, output)

    assert result["action"] == "break_loop"
    assert result["reason"] == "repeat_detected"
    assert "Current user request: fix drift" in result["replacement"]


def test_breaks_on_semantic_repeat() -> None:
    guard = LoopGuard()
    user = "fix drift"

    assert guard.check(user, "We should create a plan and move forward.")["action"] == "continue"
    result = guard.check(user, "We should create the plan and move forward.")

    assert result["action"] == "break_loop"


def test_history_is_bounded() -> None:
    guard = LoopGuard(max_history=2)
    user = "fix drift"
    first = "A unique response."
    second = "A different response."
    third = "Another response."

    assert guard.check(user, first)["action"] == "continue"
    assert guard.check(user, second)["action"] == "continue"
    assert guard.check(user, third)["action"] == "continue"

    result = guard.check(user, first)

    assert result["action"] == "continue"
