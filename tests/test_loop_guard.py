from __future__ import annotations

import pytest

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


def test_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="max_history"):
        LoopGuard(max_history=0)

    with pytest.raises(ValueError, match="similarity_threshold"):
        LoopGuard(similarity_threshold=-0.01)

    with pytest.raises(ValueError, match="similarity_threshold"):
        LoopGuard(similarity_threshold=1.01)

    with pytest.raises(ValueError, match="repeat_limit"):
        LoopGuard(repeat_limit=1)


def test_normalize_is_case_whitespace_and_punctuation_insensitive() -> None:
    guard = LoopGuard()

    assert guard.normalize("  HELLO,   World!  ") == "hello world"
    assert guard.normalize("Line\nTwo -- v1.2") == "line two -- v1.2"


def test_fingerprint_matches_normalized_equivalents() -> None:
    guard = LoopGuard()

    assert guard.fingerprint("Hello, WORLD!") == guard.fingerprint(" hello world ")


def test_similarity_is_one_for_normalized_equivalents() -> None:
    guard = LoopGuard()

    assert guard.similarity("Same answer!", "  SAME   ANSWER ") == 1.0
    assert guard.similarity("completely different", "unrelated response") < 0.88


def test_eviction_removes_old_fingerprint_count() -> None:
    guard = LoopGuard(max_history=2)
    repeated = "same response"

    guard.check("request", repeated)
    guard.check("request", "different response")
    guard.check("request", "new response")

    fingerprint = guard.fingerprint(repeated)
    assert repeated not in guard.outputs
    assert fingerprint not in guard.hashes

    result = guard.check("request", repeated)
    assert result["action"] == "continue"


def test_eviction_preserves_remaining_duplicate_count() -> None:
    guard = LoopGuard(max_history=2)
    repeated = "same response"

    guard.check("request", repeated)
    guard.check("request", repeated)
    guard.check("request", "different response")

    fingerprint = guard.fingerprint(repeated)
    assert guard.hashes[fingerprint] == 1
    assert guard.outputs == [repeated, "different response"]


def test_forward_progress_prompt_contains_required_next_action() -> None:
    guard = LoopGuard()

    prompt = guard.forward_progress_prompt("repair the broken tests")

    assert "Do not repeat the prior answer" in prompt
    assert "one concrete next action" in prompt
    assert "patch" in prompt
    assert "decision" in prompt
    assert "file classification" in prompt
    assert "specific command" in prompt
    assert "Current user request: repair the broken tests" in prompt


def test_check_records_output_before_breaking_loop() -> None:
    guard = LoopGuard()
    output = "Repeated answer"

    first = guard.check("request", output)
    second = guard.check("request", output)

    assert first["action"] == "continue"
    assert second["action"] == "break_loop"
    assert guard.outputs == [output, output]
    assert guard.hashes[guard.fingerprint(output)] == 2
