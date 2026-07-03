"""Contract tests for the deterministic type adapters.

Each adapter must (1) pass every proof on its declared self-test fixture, (2)
be pure (effects_observed == ["none"]), (3) emit an adapter_receipt, and (4)
fail cleanly (not raise) on a malformed payload. The lossy adapters must
disclose what they drop; the allow-gated auth adapter must reject a deny.
"""

import unittest

from primitives.type_adapters import REGISTRY, SELF_TESTS


class TypeAdapterContractTests(unittest.TestCase):
    def test_registry_and_fixtures_aligned(self):
        self.assertEqual(set(REGISTRY), set(SELF_TESTS),
                         "every adapter needs a self-test fixture and vice versa")

    def test_fixtures_pass_all_proofs_and_are_pure(self):
        for aid, fn in REGISTRY.items():
            with self.subTest(adapter=aid):
                out = fn(SELF_TESTS[aid])
                failed = [p.proof for p in out.proof_results if not p.passed]
                self.assertEqual(failed, [], f"{aid} fixture failed proofs {failed}")
                self.assertEqual(out.effects_observed, ["none"])
                self.assertIn("adapter_receipt", out.output)

    def test_malformed_payload_does_not_raise(self):
        for aid, fn in REGISTRY.items():
            with self.subTest(adapter=aid):
                out = fn({})
                # schema_validation must be the first proof and must have failed
                self.assertFalse(out.proof_results[0].passed,
                                 f"{aid} should fail schema_validation on empty payload")

    def test_auth_adapter_rejects_deny(self):
        out = REGISTRY["adapt:auth_decision_to_authenticated_subject"](
            {"decision": "deny", "subject": {"subject_id": "u1"}})
        gate = [p for p in out.proof_results if p.proof == "allow_decision_gate"]
        self.assertTrue(gate and not gate[0].passed)
        self.assertIsNone(out.output["authenticated_subject"])

    def test_lossy_adapters_disclose_drops(self):
        out = REGISTRY["adapt:session_grant_to_token"](
            {"token": "t", "expires_at": "z", "scope": "read"})
        receipt = out.output["adapter_receipt"]
        self.assertEqual(receipt["lossiness"], "lossy")
        self.assertEqual(sorted(receipt["fields_dropped"]), ["expires_at", "scope"])

    def test_singleton_wrap_roundtrips(self):
        out = REGISTRY["adapt:match_score_to_set"]({"pair_id": "a::b", "score": 0.5})
        self.assertEqual(out.output["match_scores"], [{"pair_id": "a::b", "score": 0.5}])


if __name__ == "__main__":
    unittest.main()
