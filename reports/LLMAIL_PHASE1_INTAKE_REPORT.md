# LLMail Phase 1 intake — 23 October 2026

The lab reports all eight pinned files downloaded successfully (about 2.115 GB decimal total), with no intake errors. Source revision `1063bdf01ec8762b812d5e06ee768a06faa5a6f7`. Exact submitted [summary](evidence/llmail_intake_20261023/llmail_phase1_intake_summary.json) is retained. File hashes are operator-reported; large source payloads remain local and have not been independently hashed by the cloud. The README digest matches the prior metadata audit.

Recorded row counts match the publisher's documented totals: 370,724 raw submissions, 160,741 annotated unique texts and 203 benign false-positive emails. Every raw row has a team field, all are nonempty according to the intake summary, and there are 224 unique teams. There are 40 level identifiers. The longest combined subject/body is 39,168 characters, so silent MiniLM truncation would invalidate coverage claims.

| Source annotation value | Unique texts |
| --- | ---: |
| `True` | 127,376 |
| `False` | 9,452 |
| `Unclear` | 23,911 |
| Malformed list | 1 |
| Numeric `1.0` | 1 |

There are 21,394 `api_triggered` and 139,347 `judge` reasons. These are source labels, not independent human adjudication. A false/unsuccessful attempt must not be automatically treated as benign. Keep the 203 publisher-designated false-positive emails distinct from these source annotations. Exclude unclear and malformed values from any initial binary fitting plan pending review; do not coerce strings with Python truthiness.

## Next: exact joins and split feasibility

No train/test split or model fitting yet. Verify local hashes, join the published text serialization to raw subject/body exactly, and report unmatched cases. Connect teams that share identical text anywhere in raw Phase 1; a large connected component could make a team-disjoint split impractical. Even a successful component split would still need near-duplicate/template checks. The index contains hashes, source labels and team/scenario metadata, not attack text. It stays in the ignored local data folder.

Terminals 1 and 2 remain stopped; run in terminal 3. This reads about 2 GB from disk and parses the 448 MB annotation JSON, so allow several GB of host RAM. No GPU, sudo, installations or new downloads are needed.

```bash
cd ~/cad_project
git pull --ff-only origin main &&
python3 scripts/audit_llmail_groups.py \
  --source-dir data/external/llmail_phase1_v1 \
  --output-dir data/external/llmail_phase1_groups_v1
```

```bash
cp ~/cad_project/data/external/llmail_phase1_groups_v1/group_audit_summary.json \
  ~/Desktop/llmail_group_audit_summary.json
```

Upload `llmail_group_audit_summary.json` only. Do not upload the SQLite index or raw payloads. If exact joins are poor, investigate publisher formatting before constructing labels or inventing task contexts. Phase 2 remains untouched; reserved evaluation independence is not established until cross-phase overlaps are checked. No v3 model has been trained.
