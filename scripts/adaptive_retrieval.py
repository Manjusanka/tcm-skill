#!/usr/bin/env python3
"""Compute a transparent retrieval budget from query and service signals."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def compute_budget(signals: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Return bounded TopK values plus replayable reason codes.

    The function consumes already extracted features. It deliberately does not ask an
    LLM to choose numerical budgets, which keeps the policy testable and framework neutral.
    """

    budget_cfg = config["retrieval"]["budget"]
    ambiguity = float(signals.get("ambiguity", 0.0))
    evidence_gap = float(signals.get("evidence_gap", 0.0))
    load_level = float(signals.get("load_level", 0.0))
    if not 0 <= ambiguity <= 1 or not 0 <= evidence_gap <= 1 or not 0 <= load_level <= 1:
        raise ValueError("ambiguity, evidence_gap, and load_level must be within [0, 1]")

    vector_k = budget_cfg["base_vector_k"]
    keyword_k = budget_cfg["base_keyword_k"]
    graph_k = 0
    fused_limit = budget_cfg["base_fused_limit"]
    rerank_k = budget_cfg["base_rerank_k"]
    reasons: list[str] = ["BASE_BUDGET"]

    if ambiguity >= 0.40:
        vector_k += round(12 * ambiguity)
        keyword_k += round(6 * ambiguity)
        fused_limit += round(12 * ambiguity)
        rerank_k += 1
        reasons.append("AMBIGUOUS_QUERY_EXPANSION")

    if signals.get("exact_token_need", False):
        keyword_k += 8
        fused_limit += 4
        reasons.append("EXACT_TOKEN_SPARSE_BOOST")

    if signals.get("multi_hop", False):
        graph_k = 10
        fused_limit += 8
        reasons.append("MULTI_HOP_GRAPH_PATH")

    risk_level = signals.get("risk_level", "low")
    if risk_level in {"high", "critical"}:
        vector_k += 8
        keyword_k += 8
        fused_limit += 12
        rerank_k += 2
        reasons.append("HIGH_RISK_EVIDENCE_EXPANSION")

    if evidence_gap >= 0.50:
        vector_k += round(8 * evidence_gap)
        keyword_k += round(4 * evidence_gap)
        fused_limit += round(8 * evidence_gap)
        reasons.append("EVIDENCE_GAP_EXPANSION")

    if load_level >= 0.80 and risk_level not in {"high", "critical"}:
        vector_k = round(vector_k * 0.75)
        keyword_k = round(keyword_k * 0.75)
        fused_limit = round(fused_limit * 0.75)
        reasons.append("LOW_RISK_LOAD_SHEDDING")
    elif load_level >= 0.80:
        reasons.append("HIGH_RISK_NO_QUALITY_SHEDDING")

    result = {
        "vector_top_k": _clamp(vector_k, 1, budget_cfg["max_vector_k"]),
        "keyword_top_k": _clamp(keyword_k, 1, budget_cfg["max_keyword_k"]),
        "graph_source_top_k": _clamp(graph_k, 0, budget_cfg["max_graph_k"]),
        "fused_candidate_limit": _clamp(
            fused_limit, rerank_k, budget_cfg["max_fused_limit"]
        ),
        "rerank_top_k": _clamp(rerank_k, 1, budget_cfg["max_rerank_k"]),
        "min_independent_sources": (
            budget_cfg["high_risk_min_sources"]
            if risk_level in {"high", "critical"}
            else 1
        ),
        "reason_codes": reasons,
    }
    return result


def load_config() -> dict[str, Any]:
    with (ROOT / "skill.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    signals = json.load(sys.stdin)
    print(json.dumps(compute_budget(signals, load_config()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
