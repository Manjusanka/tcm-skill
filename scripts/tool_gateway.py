#!/usr/bin/env python3
"""Validate a model-proposed tool plan before any adapter executes it."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def validate_plan(
    plan: dict[str, Any],
    decision: dict[str, Any],
    request_context: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    tool_family = plan.get("tool_family")
    side_effect = plan.get("side_effect")
    risk_level = decision.get("risk_level", "low")
    confidence = float(plan.get("confidence", -1))

    if tool_family not in set(decision.get("allowed_tool_families", [])):
        reasons.append("TOOL_NOT_ALLOWED_BY_DECISION")
    if tool_family not in set(request_context.get("authorized_tool_families", [])):
        reasons.append("TOOL_NOT_AUTHORIZED_FOR_REQUEST")
    if plan.get("tenant_id") != request_context.get("tenant_id"):
        reasons.append("TENANT_MISMATCH")
    if side_effect not in {"none", "read", "write"}:
        reasons.append("SIDE_EFFECT_NOT_DECLARED")
    if not isinstance(plan.get("arguments"), dict):
        reasons.append("ARGUMENTS_NOT_OBJECT")

    threshold = (
        config["routing"]["high_risk_execute_threshold"]
        if risk_level in {"high", "critical"}
        else config["routing"]["ordinary_read_execute_threshold"]
    )
    if confidence < threshold:
        reasons.append("PLAN_CONFIDENCE_BELOW_GATE")

    if side_effect == "write":
        key = plan.get("idempotency_key")
        if not isinstance(key, str) or len(key) < 8:
            reasons.append("IDEMPOTENCY_KEY_REQUIRED")
        if not plan.get("requires_confirmation", False):
            reasons.append("PLAN_CONFIRMATION_FLAG_REQUIRED")
        if not request_context.get("confirmation_received", False):
            reasons.append("USER_CONFIRMATION_REQUIRED")

    return {
        "allowed": not reasons,
        "reason_codes": reasons or ["TOOL_PLAN_VALIDATED"],
        "tool_family": tool_family,
        "side_effect": side_effect,
        "trace_id": plan.get("trace_id"),
    }


def load_config() -> dict[str, Any]:
    with (ROOT / "skill.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    payload = json.load(sys.stdin)
    result = validate_plan(
        payload["plan"], payload["decision"], payload["request_context"], load_config()
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
