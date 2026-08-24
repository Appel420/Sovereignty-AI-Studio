import tempfile
import unittest
from pathlib import Path

from sovereign.state.state_policy import StatePolicy, StateMode, evaluate_external_route
from sovereign.state.hybrid_continuity import HybridContinuityStore


class StateSovereigntyTests(unittest.TestCase):
    def test_device_only_blocks_external_execution_state(self):
        policy = StatePolicy()
        report = evaluate_external_route(policy, execution_external=True)
        self.assertTrue(report.blocked)
        self.assertFalse(report.external_data_sent)
        self.assertFalse(report.external_state_written)

    def test_device_first_allows_explicit_external_execution_without_memory(self):
        policy = StatePolicy(mode=StateMode.DEVICE_FIRST)
        report = evaluate_external_route(policy, execution_external=True)
        self.assertFalse(report.blocked)
        self.assertTrue(report.external_data_sent)
        self.assertFalse(report.external_state_written)

    def test_external_persistence_requires_policy_and_owner_authorization(self):
        policy = StatePolicy(mode=StateMode.DEVICE_FIRST, allow_external_memory=True)
        denied = evaluate_external_route(
            policy,
            execution_external=True,
            external_memory_requested=True,
            owner_authorized=False,
        )
        self.assertTrue(denied.blocked)
        self.assertFalse(denied.external_data_sent)
        self.assertFalse(denied.external_state_written)

        allowed = evaluate_external_route(
            policy,
            execution_external=True,
            external_memory_requested=True,
            owner_authorized=True,
        )
        self.assertFalse(allowed.blocked)
        self.assertTrue(allowed.external_state_written)

    def test_hybrid_is_device_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HybridContinuityStore(Path(tmp))
            record = store.append(
                who={"agent": "gpt"},
                what={"type": "task", "summary": "verified work"},
                where={"repository": "local"},
                why={"intent": "resume"},
                how={"mode": "hybrid", "network_accessed": False},
                state="VERIFIED",
                proof={"source": "local"},
            )
            self.assertEqual(record.state, "VERIFIED")
            self.assertEqual(len(store.records()), 1)


if __name__ == "__main__":
    unittest.main()
