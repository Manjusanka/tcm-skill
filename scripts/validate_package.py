#!/usr/bin/env python3
"""Validate YAML, JSON Schemas, JSONL cases, and cross-field invariants."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python -m pip install -r requirements-dev.txt") from exc


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_skill_config() -> dict:
    with (ROOT / "skill.yaml").open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    require(config["name"] == ROOT.name, "skill.yaml name must match the folder name")
    routing = config["routing"]
    require(
        0 <= routing["clarification_threshold"]
        <= routing["ordinary_read_execute_threshold"]
        <= routing["high_risk_execute_threshold"]
        <= 1,
        "routing thresholds must be ordered within [0, 1]",
    )

    retrieval = config["retrieval"]
    require(
        retrieval["rerank_top_k"] <= retrieval["fused_candidate_limit"],
        "rerank_top_k cannot exceed fused_candidate_limit",
    )
    source_total = (
        retrieval["vector_top_k"]
        + retrieval["keyword_top_k"]
        + retrieval["graph_source_top_k"]
    )
    require(
        retrieval["fused_candidate_limit"] <= source_total,
        "fused_candidate_limit exceeds all candidate sources combined",
    )

    chunking = config["chunking"]
    require(
        chunking["min_tokens"]
        < chunking["target_tokens"]
        <= chunking["soft_max_tokens"]
        <= chunking["hard_max_tokens"],
        "chunk token limits must be ordered",
    )
    require(
        chunking["overlap_tokens"] < chunking["min_tokens"],
        "overlap_tokens must be smaller than min_tokens",
    )

    context = config["context"]
    allocated = (
        context["output_reserve_tokens"]
        + context["evidence_max_tokens"]
        + context["memory_max_tokens"]
    )
    require(allocated <= context["total_tokens"], "context allocations exceed total_tokens")
    require(
        context["tool_result_max_tokens"] <= context["evidence_max_tokens"],
        "tool_result_max_tokens should fit within evidence capacity",
    )

    tools = config["tools"]
    require(
        tools["max_same_tool_calls"] <= tools["max_total_calls"],
        "max_same_tool_calls cannot exceed max_total_calls",
    )
    require(
        tools["max_parallel_calls"] <= tools["max_total_calls"],
        "max_parallel_calls cannot exceed max_total_calls",
    )
    return config


def validate_json_schemas() -> int:
    count = 0
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        schema = load_json(path)
        require(isinstance(schema, dict), f"{path.name} must contain an object")
        require(
            schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
            f"{path.name} must use JSON Schema 2020-12",
        )
        require("title" in schema and "type" in schema, f"{path.name} lacks title or type")
        count += 1
    require(count >= 3, "expected at least three JSON Schemas")
    return count


def validate_eval_cases() -> int:
    path = ROOT / "references" / "eval-cases.jsonl"
    ids: set[str] = set()
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            case = json.loads(raw)
            require(case.get("id"), f"eval line {line_number} is missing id")
            require(case["id"] not in ids, f"duplicate eval id: {case['id']}")
            require(
                case.get("mode") in {"answer", "audit", "design"},
                f"invalid mode on eval line {line_number}",
            )
            require(bool(case.get("query")), f"eval line {line_number} is missing query")
            require(
                isinstance(case.get("expected"), dict),
                f"eval line {line_number} is missing expected object",
            )
            ids.add(case["id"])
            count += 1
    require(count >= 8, "expected at least eight smoke evaluation cases")
    return count


def validate_required_files() -> None:
    required = [
        "SKILL.md",
        "agents/openai.yaml",
        "skill.yaml",
        "references/retrieval-and-context.md",
        "references/tools-and-agent.md",
        "references/safety-and-versioning.md",
        "references/evaluation.md",
        "references/prompt-templates.md",
    ]
    for relative in required:
        require((ROOT / relative).is_file(), f"missing required file: {relative}")


def main() -> int:
    try:
        validate_required_files()
        config = validate_skill_config()
        schema_count = validate_json_schemas()
        eval_count = validate_eval_cases()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(
        "OK: validated "
        f"{config['name']} v{config['version']}; "
        f"{schema_count} schemas; {eval_count} evaluation cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
