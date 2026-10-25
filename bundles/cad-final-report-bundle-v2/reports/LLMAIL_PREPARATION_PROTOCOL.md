# LLMail Phase 1 preparation — frozen exact-component split

The corrected lab grouping summary reconciles: 127,376 total source positives, 9,452 source negatives, 23,911 unclear and two malformed values. Among matched texts there are 127,370 positives, 9,452 negatives, 23,910 unclear and two malformed. Seven unmatched annotations remain outside contextual exports. Source hashes match the prior intake; current grouping source digest matches the recorded script. Component label counts sum exactly to the matched totals. This is reconciliation of operator-supplied metadata, not independent parsing of the source corpus.

The [corrected summary](evidence/llmail_groups_corrected_20261023/llmail_group_audit_corrected.json) and [fixed split plan](evidence/llmail_groups_corrected_20261023/component_split_plan.json) are retained. All 142 components receive one split. Sort by decreasing number of definite-label texts, break ties by component hash, then assign each whole component to the largest remaining 70/15/15 count target deficit. No classifier outputs or performance measurements are used. Large components make exact ratios impossible with this rule.

| Split | Source True | Source False | Total |
| --- | ---: | ---: | ---: |
| Training | 93,716 | 8,033 | 101,749 |
| Validation | 17,089 | 448 | 17,537 |
| Reserved Phase 1 test | 16,565 | 971 | 17,536 |

These are source annotation targets, not human-reviewed attack/benign truth. Class imbalance and differing negative proportions must be reported; accuracy alone is inadequate. Keep the 203 publisher benign emails separate for later false-positive evaluation. Phase 2 remains untouched and is only a candidate external test until overlap is checked. Exact component separation does not eliminate near-duplicate or template leakage.

## Local export in terminal 3

Keep vLLM and gateway stopped. No GPU, downloads or training. This reads the local annotation JSON and audited SQLite index, verifies source checksums and component counts, and writes source-labeled JSONL files under the ignored data directory. Allow several GB of RAM and additional disk space for exported text.

```bash
cd ~/cad_project
git pull --ff-only origin main &&
python3 scripts/prepare_llmail_phase1.py \
  --source-dir data/external/llmail_phase1_v1 \
  --group-dir data/external/llmail_phase1_groups_v2 \
  --output-dir data/external/llmail_phase1_prepared_v1
```

```bash
cp ~/cad_project/data/external/llmail_phase1_prepared_v1/preparation_summary.json \
  ~/Desktop/llmail_preparation_summary.json
```

Upload only `llmail_preparation_summary.json`. Do not upload or commit split JSONL payloads. Do not inspect or tune against reserved test cases. No model fitting is performed; running this once creates artifacts for the next engineering step.

## Input contract and remaining boundaries

For each matched annotation, choose the lexicographically first observed raw level to associate one observed scenario. The exported `task` is that scenario's legitimate `user_query`, never its attacker `task`. `untrusted_content` is the unchanged annotation text (serialized subject and body). Each unique annotated email appears once. If the email occurred under multiple scenarios, this deterministic projection retains one, not every possible contextual interpretation.

This is a **one-email projection**, not the full original retrieval context, tool schema or agent execution. Source labels remain `source_attack_attempt` and `source_reason`; no downstream attack success is inferred. Unclear/malformed and unmatched definite texts are excluded with counts. The index/group file is checked against the fixed plan; artifacts from the earlier uncorrected audit are not accepted.

Tokenization/windowing is still required before embeddings: emails reach 39,168 characters. This export does not truncate, tokenize or silently discard long inputs. Before fitting, implement explicit long-input coverage and near-duplicate checks using development data, then freeze handling before reserved scoring. Batching or exceeding the MiniLM token limit without such handling would not be a valid evaluation.
