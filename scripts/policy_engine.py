#!/usr/bin/env python3
"""Deterministic, framework-neutral routing and safety policy engine."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from adaptive_retrieval import compute_budget


ROOT = Path(__file__).resolve().parents[1]
HIGH_RISK_FLAGS = {
    "dosage",
    "toxicity",
    "pregnancy",
    "child",
    "elderly",
    "liver_kidney_impairment",
    "allergy",
    "drug_interaction",
    "treatment_change",
}


def _risk_level(signals: dict[str, Any]) -> str:
    if signals.get("emergency", False):
        return "critical"
    flags = set(signals.get("risk_flags", []))
    if flags & HIGH_RISK_FLAGS:
        return "high"
    if signals.get("medical_personalization", False):
        return "medium"
    return "low"


def decide(signals: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Turn semantic features into a policy decision without framework APIs."""

    risk = _risk_level(signals)
    confidence = float(signals.get("confidence", 1.0))
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be within [0, 1]")

    reasons: list[str] = []
    allowed_tools: list[str] = []
    requires_human = risk in {"high", "critical"}

    budget_signals = {
        "ambiguity": signals.get("ambiguity", 0.0),
        "evidence_gap": signals.get("evidence_gap", 0.0),
        "load_level": signals.get("load_level", 0.0),
        "exact_token_need": signals.get("requires_exact_value", False),
        "multi_hop": signals.get("multi_hop", False),
        "risk_level": risk,
    }
    retrieval_budget = compute_budget(budget_signals, config)

    needs_tool = signals.get("requires_fresh_data", False) or signals.get(
        "requires_exact_value", False
    )

    if not signals.get("permission_ok", True):
        route = "refuse"
        reasons.append("PERMISSION_DENIED")
    elif signals.get("emergency", False):
        route = "emergency"
        reasons.append("EMERGENCY_ESCALATION")
    elif risk == "high" and signals.get("missing_decisive_facts", False):
        route = "clarify"
        reasons.append("HIGH_RISK_FACTS_MISSING")
    elif risk == "high" and confidence < config["routing"]["high_risk_execute_threshold"]:
        route = "clarify"
        reasons.append("HIGH_RISK_CONFIDENCE_BELOW_GATE")
    elif confidence < config["routing"]["clarification_threshold"]:
        route = "clarify"
        reasons.append("ROUTING_CONFIDENCE_LOW")
    elif needs_tool and confidence < config["routing"]["ordinary_read_execute_threshold"]:
        route = "clarify"
        reasons.append("TOOL_CONFIDENCE_BELOW_GATE")
    elif signals.get("write_requested", False):
        route = "tool"
        requires_human = True
        reasons.extend(["WRITE_REQUIRES_CONFIRMATION", "IDEMPOTENCY_REQUIRED"])
    else:
        needs_graph = signals.get("multi_hop", False)
        needs_memory = signals.get("use_history", False)
        selected = sum([bool(needs_tool), bool(needs_graph), bool(needs_memory)])
        if selected > 1:
            route = "hybrid"
            reasons.append("MULTIPLE_CAPABILITY_SOURCES")
        elif needs_tool:
            route = "tool"
            reasons.append("CURRENT_OR_EXACT_STATE_REQUIRED")
        elif needs_graph:
            route = "graph"
            reasons.append("MULTI_HOP_RELATION_REQUIRED")
        elif needs_memory:
            route = "memory"
            reasons.append("CONFIRMED_HISTORY_RELEVANT")
        else:
            route = "retrieve"
            reasons.append("STABLE_KNOWLEDGE_QUERY")

        if needs_tool:
            allowed_tools.append(
                "interaction_rule_check"
                if "drug_interaction" in set(signals.get("risk_flags", []))
                else "read_structured_record"
            )
        if needs_graph:
            allowed_tools.append("knowledge_graph_query")
        allowed_tools.append("hybrid_document_search")

    return {
        "risk_level": risk,
        "route": route,
        "confidence": confidence,
        "reason_codes": reasons + retrieval_budget["reason_codes"],
        "allowed_tool_families": sorted(set(allowed_tools)),
        "retrieval_budget": retrieval_budget,
        "requires_human": requires_human,
        "policy_version": config["version"],
    }


def load_config() -> dict[str, Any]:
    with (ROOT / "skill.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    signals = json.load(sys.stdin)
    print(json.dumps(decide(signals, load_config()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
