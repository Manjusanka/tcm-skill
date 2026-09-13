#!/usr/bin/env python3
"""Validate claim-to-evidence links independently from answer generation."""

from __future__ import annotations

import json
import sys
from typing import Any


FACTUAL_KINDS = {"factual", "dosage", "contraindication", "interaction"}
HIGH_RISK_KINDS = {"dosage", "contraindication", "interaction"}


def validate_answer(answer: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    evidence_items = ledger.get("evidence", [])
    evidence_by_id = {item["evidence_id"]: item for item in evidence_items}
    if len(evidence_by_id) != len(evidence_items):
        violations.append({"code": "DUPLICATE_EVIDENCE_ID", "severity": "critical"})

    active_release = ledger.get("active_release_id")
    citations = answer.get("citations", [])
    declared_citations = {item.get("evidence_id") for item in citations if item.get("evidence_id")}

    for citation in citations:
        citation_id = citation.get("evidence_id")
        if citation_id not in evidence_by_id:
            violations.append(
                {"code": "UNKNOWN_CITATION", "severity": "critical", "evidence_id": citation_id}
            )
            continue
        ledger_item = evidence_by_id[citation_id]
        if not ledger_item.get("authorized", False):
            violations.append(
                {"code": "UNAUTHORIZED_CITATION", "severity": "critical", "evidence_id": citation_id}
            )
        if ledger_item.get("status") != "ACTIVE" or ledger_item.get("release_id") != active_release:
            violations.append(
                {"code": "OBSOLETE_CITATION", "severity": "critical", "evidence_id": citation_id}
            )
        if citation.get("release_id") != ledger_item.get("release_id"):
            violations.append(
                {"code": "CITATION_RELEASE_MISMATCH", "severity": "critical", "evidence_id": citation_id}
            )
        if citation.get("document_version") != ledger_item.get("document_version"):
            violations.append(
                {"code": "CITATION_VERSION_MISMATCH", "severity": "critical", "evidence_id": citation_id}
            )
        if citation.get("source_title") != ledger_item.get("source_title"):
            violations.append(
                {"code": "CITATION_TITLE_MISMATCH", "severity": "high", "evidence_id": citation_id}
            )

    claims = answer.get("claims", [])
    claim_ids = [claim.get("claim_id") for claim in claims]
    if any(not claim_id for claim_id in claim_ids):
        violations.append({"code": "MISSING_CLAIM_ID", "severity": "critical"})
    if len(set(claim_ids)) != len(claim_ids):
        violations.append({"code": "DUPLICATE_CLAIM_ID", "severity": "critical"})

    for claim in claims:
        claim_id = claim.get("claim_id")
        kind = claim.get("kind")
        evidence_ids = claim.get("evidence_ids", [])
        if kind in FACTUAL_KINDS and not evidence_ids:
            violations.append(
                {"code": "UNSUPPORTED_CLAIM", "severity": "critical", "claim_id": claim_id}
            )
        for evidence_id in evidence_ids:
            item = evidence_by_id.get(evidence_id)
            if item is None:
                violations.append(
                    {
                        "code": "UNKNOWN_EVIDENCE",
                        "severity": "critical",
                        "claim_id": claim_id,
                        "evidence_id": evidence_id,
                    }
                )
                continue
            if evidence_id not in declared_citations:
                violations.append(
                    {
                        "code": "CLAIM_CITATION_NOT_DECLARED",
                        "severity": "high",
                        "claim_id": claim_id,
                        "evidence_id": evidence_id,
                    }
                )
            if not item.get("authorized", False):
                violations.append(
                    {
                        "code": "UNAUTHORIZED_EVIDENCE",
                        "severity": "critical",
                        "claim_id": claim_id,
                        "evidence_id": evidence_id,
                    }
                )
            if item.get("status") != "ACTIVE" or item.get("release_id") != active_release:
                violations.append(
                    {
                        "code": "OBSOLETE_OR_WRONG_RELEASE",
                        "severity": "critical",
                        "claim_id": claim_id,
                        "evidence_id": evidence_id,
                    }
                )
            if kind in HIGH_RISK_KINDS and not item.get("authoritative", False):
                violations.append(
                    {
                        "code": "HIGH_RISK_SOURCE_NOT_AUTHORITATIVE",
                        "severity": "critical",
                        "claim_id": claim_id,
                        "evidence_id": evidence_id,
                    }
                )

    if answer.get("risk_level") in {"high", "critical"} and not answer.get("safety_note"):
        violations.append({"code": "HIGH_RISK_SAFETY_NOTE_MISSING", "severity": "high"})

    critical = sum(1 for item in violations if item["severity"] == "critical")
    return {
        "passed": critical == 0,
        "critical_count": critical,
        "violation_count": len(violations),
        "violations": violations,
    }


def main() -> int:
    payload = json.load(sys.stdin)
    print(
        json.dumps(
            validate_answer(payload["answer"], payload["ledger"]),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
