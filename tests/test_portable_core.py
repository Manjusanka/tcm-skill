from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adaptive_retrieval import compute_budget, load_config  # noqa: E402
from context_compiler import compile_context  # noqa: E402
from evidence_guard import validate_answer  # noqa: E402
from policy_engine import decide  # noqa: E402
from tool_gateway import validate_plan  # noqa: E402


class AdaptiveRetrievalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()

    def test_high_risk_expands_evidence_budget(self) -> None:
        low = compute_budget({"risk_level": "low"}, self.config)
        high = compute_budget({"risk_level": "high"}, self.config)
        self.assertGreater(high["vector_top_k"], low["vector_top_k"])
        self.assertGreater(high["min_independent_sources"], low["min_independent_sources"])

    def test_load_shedding_does_not_reduce_high_risk_quality(self) -> None:
        high = compute_budget({"risk_level": "high", "load_level": 0.95}, self.config)
        self.assertIn("HIGH_RISK_NO_QUALITY_SHEDDING", high["reason_codes"])
        self.assertNotIn("LOW_RISK_LOAD_SHEDDING", high["reason_codes"])


class PolicyEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()

    def test_permission_denial_precedes_retrieval(self) -> None:
        decision = decide({"permission_ok": False}, self.config)
        self.assertEqual(decision["route"], "refuse")
        self.assertEqual(decision["allowed_tool_families"], [])

    def test_interaction_uses_rule_tool_and_human_review(self) -> None:
        decision = decide(
            {
                "risk_flags": ["drug_interaction"],
                "requires_fresh_data": True,
                "confidence": 0.95,
            },
            self.config,
        )
        self.assertEqual(decision["route"], "tool")
        self.assertIn("interaction_rule_check", decision["allowed_tool_families"])
        self.assertTrue(decision["requires_human"])

    def test_emergency_short_circuits_agent_loop(self) -> None:
        decision = decide({"emergency": True}, self.config)
        self.assertEqual(decision["route"], "emergency")
        self.assertTrue(decision["requires_human"])

    def test_high_risk_low_confidence_must_clarify(self) -> None:
        decision = decide({"risk_flags": ["dosage"], "confidence": 0.80}, self.config)
        self.assertEqual(decision["route"], "clarify")
        self.assertIn("HIGH_RISK_CONFIDENCE_BELOW_GATE", decision["reason_codes"])


class ContextCompilerTest(unittest.TestCase):
    def test_selects_complementary_evidence(self) -> None:
        result = compile_context(
            [
                {"evidence_id": "a", "token_cost": 100, "covers": ["c1"], "score": 0.9},
                {"evidence_id": "b", "token_cost": 100, "covers": ["c1"], "score": 0.8},
                {"evidence_id": "c", "token_cost": 100, "covers": ["c2"], "score": 0.7},
            ],
            token_budget=200,
        )
        self.assertEqual(set(result["selected_evidence_ids"]), {"a", "c"})
        self.assertEqual(result["covered_claims"], ["c1", "c2"])

    def test_never_truncates_mandatory_evidence(self) -> None:
        result = compile_context(
            [{"evidence_id": "a", "token_cost": 300, "covers": ["c1"], "mandatory": True}],
            token_budget=200,
        )
        self.assertEqual(result["status"], "insufficient_budget_for_mandatory_evidence")


class ToolGatewayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()
        self.decision = {
            "risk_level": "low",
            "allowed_tool_families": ["hybrid_document_search"],
        }
        self.context = {
            "tenant_id": "tenant-a",
            "authorized_tool_families": ["hybrid_document_search"],
            "confirmation_received": False,
        }

    def plan(self) -> dict:
        return {
            "tool_family": "hybrid_document_search",
            "purpose": "retrieve evidence",
            "side_effect": "read",
            "arguments": {"query": "test"},
            "confidence": 0.90,
            "tenant_id": "tenant-a",
            "expected_output_fields": ["evidence_id"],
            "trace_id": "trace-1",
        }

    def test_allows_valid_read_plan(self) -> None:
        result = validate_plan(self.plan(), self.decision, self.context, self.config)
        self.assertTrue(result["allowed"])

    def test_rejects_wrong_tool(self) -> None:
        plan = self.plan()
        plan["tool_family"] = "read_structured_record"
        result = validate_plan(plan, self.decision, self.context, self.config)
        self.assertFalse(result["allowed"])
        self.assertIn("TOOL_NOT_ALLOWED_BY_DECISION", result["reason_codes"])

    def test_rejects_write_without_confirmation_and_idempotency(self) -> None:
        plan = self.plan()
        plan["side_effect"] = "write"
        plan["requires_confirmation"] = True
        result = validate_plan(plan, self.decision, self.context, self.config)
        self.assertFalse(result["allowed"])
        self.assertIn("IDEMPOTENCY_KEY_REQUIRED", result["reason_codes"])
        self.assertIn("USER_CONFIRMATION_REQUIRED", result["reason_codes"])


class EvidenceGuardTest(unittest.TestCase):
    @staticmethod
    def ledger(status: str = "ACTIVE", authorized: bool = True) -> dict:
        return {
            "tenant_id": "tenant-a",
            "active_release_id": "release-2",
            "evidence": [
                {
                    "evidence_id": "e1",
                    "source_title": "reviewed source",
                    "release_id": "release-2",
                    "document_version": "v2",
                    "status": status,
                    "authorized": authorized,
                    "authoritative": True,
                    "reviewed": True,
                    "independence_group": "guide-a",
                    "content_hash": "12345678",
                }
            ],
        }

    @staticmethod
    def answer() -> dict:
        return {
            "conclusion": "需要专业人员复核。",
            "claims": [
                {
                    "claim_id": "c1",
                    "text": "存在相互作用风险。",
                    "kind": "interaction",
                    "evidence_ids": ["e1"],
                }
            ],
            "citations": [
                {
                    "evidence_id": "e1",
                    "source_title": "reviewed source",
                    "release_id": "release-2",
                    "document_version": "v2",
                }
            ],
            "risk_level": "high",
            "disposition": "escalate",
            "safety_note": "请由医生或药师复核。",
        }

    def test_accepts_authorized_active_evidence(self) -> None:
        self.assertTrue(validate_answer(self.answer(), self.ledger())["passed"])

    def test_rejects_obsolete_evidence(self) -> None:
        result = validate_answer(self.answer(), self.ledger(status="DEPRECATED"))
        self.assertFalse(result["passed"])
        self.assertIn("OBSOLETE_OR_WRONG_RELEASE", {v["code"] for v in result["violations"]})

    def test_rejects_unauthorized_evidence(self) -> None:
        result = validate_answer(self.answer(), self.ledger(authorized=False))
        self.assertFalse(result["passed"])
        self.assertIn("UNAUTHORIZED_EVIDENCE", {v["code"] for v in result["violations"]})

    def test_rejects_unused_unauthorized_citation(self) -> None:
        ledger = self.ledger()
        ledger["evidence"].append(
            {
                "evidence_id": "e2",
                "source_title": "private source",
                "release_id": "release-2",
                "document_version": "v2",
                "status": "ACTIVE",
                "authorized": False,
                "authoritative": True,
                "reviewed": True,
                "independence_group": "private",
                "content_hash": "abcdefgh",
            }
        )
        answer = self.answer()
        answer["citations"].append(
            {
                "evidence_id": "e2",
                "source_title": "private source",
                "release_id": "release-2",
                "document_version": "v2",
            }
        )
        result = validate_answer(answer, ledger)
        self.assertFalse(result["passed"])
        self.assertIn("UNAUTHORIZED_CITATION", {v["code"] for v in result["violations"]})


if __name__ == "__main__":
    unittest.main()
