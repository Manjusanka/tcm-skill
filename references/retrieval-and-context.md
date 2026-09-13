# Retrieval and context assembly

## Indexing path

Use a structure-first pipeline: ingest -> malware/type check -> parser selection -> layout recovery -> normalization -> semantic/structural chunking -> metadata enrichment -> embedding and keyword index -> quality checks -> staged release -> atomic activation.

Do not confuse embedding dimension with chunk length. The default chunk settings in `skill.yaml` are starting points for encoders with a roughly 512-token input limit. Preserve headings, lists, table captions, page numbers, negation, dosage units, and source offsets. Merge tiny adjacent sections when they share a heading and meaning. Keep a stable `logical_chunk_id` across document revisions and a unique `chunk_version_id` per immutable version.

For complex PDFs, route by page or region instead of forcing one parser:

- digital text: layout-aware extraction;
- scanned pages: OCR with confidence and coordinates;
- tables: cell grid plus a readable linearization, retaining title and units;
- formulas/images: store bounding box, caption, OCR/recognition result, and page image reference;
- low-confidence regions: quarantine for review rather than indexing corrupted text.

## Online retrieval

1. Rewrite only when necessary; retain original query and medical constraints.
2. Apply tenant, ACL, release, status, language, source type, and validity filters.
3. Run dense retrieval for semantic paraphrases and sparse/keyword retrieval for exact terms, rare entities, codes, numbers, and drug names.
4. Optionally query the graph for multi-hop relations, then map graph facts back to `source_chunk_id`.
5. Fuse by rank, not incomparable raw scores. Reciprocal Rank Fusion uses `score(d)=sum(1/(k+rank_i(d)))`; `k=60` is a tunable default.
6. Deduplicate by semantic content and collapse versions by `logical_chunk_id` before reranking.
7. Rerank at query-passage granularity and retain a small evidence set. Expand the parent or neighboring chunk only after selection.

More candidates are not always better. Large TopK increases reranker cost, latency, duplicate evidence, context competition, and the chance of admitting plausible but wrong passages. Tune candidate and final TopK independently using Recall@K, nDCG/MRR, answer correctness, citation faithfulness, latency, and token cost.

## Metadata as an active signal

Use metadata for hard filtering before recall and calibrated ranking after recall:

- identity: tenant, ACL, document, logical chunk, version;
- lifecycle: status, release, effective time, expiry, supersedes;
- structure: title path, page, section, table/figure, parent chunk;
- domain: disease, syndrome, herb, formula, population, evidence level;
- quality: parser confidence, review state, authority, freshness;
- provenance: source URI, checksum, ingested time, parser/model version.

Freshness must not override validity. A current but low-authority source should not automatically beat an authoritative source, and an obsolete version should normally be filtered rather than merely down-weighted.

## Memory retrieval

Separate recent conversation, structured confirmed memory, and optional semantic long-term memory. Apply hard filters by tenant/user/conversation, status, consent, sensitivity, and expiry. Rank eligible memories using task relevance, entity match, recency, importance, and source reliability.

Store `source_turn_id`, confirmation state, expiry, and `supersedes` links. Never store a generated inference as a confirmed fact. When two high-risk facts conflict, ask the user rather than selecting one by similarity.

## Context assembly order

Assemble: system/safety rules -> normalized user request -> relevant confirmed memory -> current evidence -> normalized tool results -> output constraints. Keep source boundaries explicit. Reserve output capacity first and drop low-value context by marginal evidence gain, not by truncating the middle of a citation.
