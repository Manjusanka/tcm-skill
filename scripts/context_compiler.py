#!/usr/bin/env python3
"""Select atomic evidence units by marginal claim coverage under a token budget."""

from __future__ import annotations

import json
import sys
from typing import Any


def compile_context(
    candidates: list[dict[str, Any]],
    token_budget: int,
    claim_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    if token_budget <= 0:
        raise ValueError("token_budget must be positive")
    weights = claim_weights or {}
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    covered: set[str] = set()
    used = 0

    def add(item: dict[str, Any]) -> None:
        nonlocal used
        selected.append(item)
        selected_ids.add(item["evidence_id"])
        covered.update(item.get("covers", []))
        used += int(item["token_cost"])

    mandatory = sorted(
        (item for item in candidates if item.get("mandatory", False)),
        key=lambda item: (-float(item.get("score", 0)), item["evidence_id"]),
    )
    for item in mandatory:
        cost = int(item["token_cost"])
        if cost <= 0:
            raise ValueError("token_cost must be positive")
        if used + cost > token_budget:
            return {
                "status": "insufficient_budget_for_mandatory_evidence",
                "selected_evidence_ids": [x["evidence_id"] for x in selected],
                "used_tokens": used,
                "covered_claims": sorted(covered),
            }
        add(item)

    remaining = [item for item in candidates if item["evidence_id"] not in selected_ids]
    while remaining:
        feasible = [item for item in remaining if used + int(item["token_cost"]) <= token_budget]
        if not feasible:
            break

        def utility(item: dict[str, Any]) -> tuple[float, float, str]:
            new_claims = set(item.get("covers", [])) - covered
            coverage_gain = sum(float(weights.get(claim, 1.0)) for claim in new_claims)
            quality = float(item.get("score", 0.0))
            density = (coverage_gain + 0.15 * quality) / int(item["token_cost"])
            return density, quality, item["evidence_id"]

        best = max(feasible, key=utility)
        add(best)
        remaining.remove(best)

    return {
        "status": "ok",
        "selected_evidence_ids": [item["evidence_id"] for item in selected],
        "used_tokens": used,
        "covered_claims": sorted(covered),
        "remaining_tokens": token_budget - used,
    }


def main() -> int:
    payload = json.load(sys.stdin)
    result = compile_context(
        payload["candidates"], payload["token_budget"], payload.get("claim_weights")
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
