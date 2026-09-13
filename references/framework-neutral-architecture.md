# Framework-neutral architecture

## Boundary

The core is a protocol, not an Agent framework. It accepts structured query signals and produces structured decisions, context selections, tool plans, and evidence-validation results. A runtime adapter owns model calls, transport, persistence, and framework-specific state.

```text
Framework adapter
  -> semantic feature extractor
  -> deterministic policy engine
  -> capability graph
       -> retrieval adapter
       -> graph adapter
       -> memory adapter
       -> tool gateway
  -> context compiler
  -> generation adapter
  -> independent evidence guard
  -> answer contract
```

## Portable core

- `skill.yaml`: versioned manifest, fallback limits, and invariant switches;
- `schemas/query.schema.json`: external request contract;
- `schemas/decision.schema.json`: replayable routing result;
- `schemas/tool-plan.schema.json`: side-effect-declared plan before execution;
- `schemas/tool-result.schema.json`: normalized dependency result;
- `schemas/evidence-ledger.schema.json`: immutable evidence snapshot;
- `schemas/answer.schema.json`: claim-level output contract;
- `scripts/policy_engine.py`: deterministic risk and route selection;
- `scripts/adaptive_retrieval.py`: explainable per-query retrieval budget;
- `scripts/context_compiler.py`: atomic context selection by marginal claim coverage;
- `scripts/tool_gateway.py`: validate side effects, tenant, authorization, confidence, and idempotency;
- `scripts/evidence_guard.py`: independent claim/evidence authorization and version gate.

These components use stdin/stdout JSON and ordinary files. A service may expose them as an in-process library, subprocess, HTTP service, or sidecar without changing their semantics.

## Adapter responsibilities

| Adapter | Must implement | Must not change |
|---|---|---|
| Codex | load `SKILL.md` and references | portable schemas and safety invariants |
| Spring AI | map Advisors/Tools to capability calls | decision reason codes and tool gateway order |
| LangGraph | map capability graph to nodes/edges | policy decisions and evidence ledger semantics |
| MCP host | map logical tool families to MCP tools | authorization, result normalization, write confirmation |
| Custom C++/Java service | call scripts or port pure functions | contract tests and release gates |

Framework state must not become the source of truth for authorization or document lifecycle. Those decisions belong to the policy and data layers.

## Capability graph instead of a fixed chain

The workflow is a bounded directed graph with guarded transitions:

- emergency and permission failures short-circuit before retrieval;
- retrieval, graph, memory, and real-time tools may run independently or as a hybrid plan;
- all evidence converges into a ledger before context compilation;
- generation cannot execute external writes;
- the evidence guard can return `pass`, `repair`, `partial`, `refuse`, or `escalate`;
- loops are bounded by call, step, and same-tool limits.

The graph separates semantic reasoning from policy enforcement: a model may extract ambiguous intent, but deterministic code decides whether the resulting action is permitted.

## Innovation boundary

The design is an engineering integration innovation: it combines known ideas—policy-as-code, hybrid retrieval, evidence provenance, bounded agents, and adaptive budgeting—into a testable Skill protocol. Do not claim a new retrieval algorithm or medical breakthrough without controlled experiments and publication-grade evidence.
