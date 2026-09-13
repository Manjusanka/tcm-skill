# Evaluation and release gates

## Build the evaluation set

Sample real tasks by intent, domain entity, query length, ambiguity, risk level, source version, and failure history. Keep a frozen regression set and a rotating recent-traffic set. Include adversarial prompt injection, cross-tenant attempts, obsolete-version traps, conflicting evidence, empty retrieval, tool timeouts, and malformed tables.

Annotate expected intent, required facts, acceptable source chunks, unsafe actions, expected tool family, and whether clarification or refusal is required. Double-label a risk-weighted subset and adjudicate disagreements.

## Stage metrics

Do not judge the entire system with one score. Store the first failing stage for each case: semantic extraction, policy, permission/version filter, recall, fusion, rerank, tool validation, tool execution, context compile, generation, or evidence guard.

- routing: intent macro-F1, tool selection accuracy, unnecessary-call rate;
- retrieval: Recall@K, MRR/nDCG, version accuracy, ACL violation count, duplicate rate;
- reranking: nDCG@K, pairwise accuracy, latency;
- generation: answer correctness, citation precision/recall, faithfulness, completeness, conflict handling;
- tools: argument validity, success rate, wrong-tool rate, retry recovery, timeout rate;
- memory: relevant-memory recall, stale/conflicting memory rate, cross-user leakage count;
- safety: unsafe-answer rate, critical violation count, refusal precision/recall, injection success rate;
- system: P50/P95/P99 latency, throughput, error rate, token and tool cost.

For real user queries, also measure task completion, reformulation rate, escalation rate, repeated-question rate, thumbs/ratings with bias controls, and time to resolution. Query text alone is insufficient; retain answer, evidence IDs, tool trace, versions, latency, and feedback.

## Experiment design

Change one major variable at a time: chunking, filters, candidate TopK, fusion, reranker, context budget, prompt, policy, or model. Compare against the same frozen set and report confidence intervals or repeated-run variance for stochastic generation. Replay the saved semantic signals, policy version, release ID, candidate IDs, selected context, tool results, and claim-evidence edges. Inspect failures by stage; an answer failure with correct retrieval is not a retrieval failure.

The numerical settings in `skill.yaml` are initial engineering defaults, not claimed production benchmarks. Tune them on the target corpus and hardware.

## Suggested release gates

- zero critical safety, fabricated-citation, and cross-tenant failures in the release suite;
- no regression beyond the team's agreed tolerance on high-risk slices;
- retrieval and citation gains must survive end-to-end evaluation;
- P95/P99 latency and cost remain within the service SLO;
- rollback release and active-pointer switch are tested.

Use `references/eval-cases.jsonl` as a small contract smoke suite, not as proof of medical quality.
