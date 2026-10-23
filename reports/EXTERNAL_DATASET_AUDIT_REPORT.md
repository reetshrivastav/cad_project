# External dataset audit — 23 October 2026

Proceed with a pinned LLMail Phase 1 intake. Its dataset card declares MIT and lists contextual metadata, source annotations and a benign false-positive collection. Defer Tensor Trust reuse until its applicable data license is established.

The exact uploaded [audit archive](evidence/external_dataset_audit_20261023/cad-external-dataset-audit-v1.tar.gz) and [verified summary](evidence/external_dataset_audit_20261023/verified_summary.json) preserve revision IDs and documentation hashes. Every recorded document digest and byte count reconciles. The lab reported all three sources completed, but both GitHub tree requests were rate-limited (403), so file listings were incomplete. This does not prevent use of the successful Hugging Face listing. No attack payloads were collected in this metadata audit.

LLMail revision: `1063bdf01ec8762b812d5e06ee768a06faa5a6f7`. Its card documents 370,724 Phase 1 raw submissions, 160,741 uniquely annotated Phase 1 texts and 203 false-positive emails; these are publisher counts, not yet locally verified. Phase 2 remains a candidate for later reserved evaluation, subject to team/near-duplicate overlap checks; chronology alone does not make it independent.

Important schema findings:

- Raw submissions include subject/body, team ID, scenario, timestamps and objective flags. Repeated submissions across levels must not be split randomly across training and test.
- Unique-text annotations include `attack_attempt`, `reason` and sometimes judge category/answer. Labels may come from tool triggering or an LLM judge, not independent human adjudication. Attack success, attack intent and benignness are distinct. Do not relabel a failed attack as benign.
- `scenarios.json` documents legitimate `user_query`, context emails, insertion position and attacker `task`. The latter is the adversary objective, not the legitimate task. Preserve this distinction in any adapter.
- The README contains stale/inconsistent links: the repository listing shows `emails_for_fp_tests.json` (not `.jsonl`), and the Phase 2 unique-data hyperlink points to Phase 1. Intake must use the verified listing, not copy those links.
- Tensor Trust revision `747a75e096761ebc01bd3970158827326b4add23` has no collected root license. The Microsoft analysis repository's MIT license does not establish Tensor Trust data rights.

## Next lab step

Keep terminals 1 and 2 stopped. Terminal 3 downloads pinned Phase 1 files and context/benign support files, calculates local digests, and summarizes schemas without printing attack text. No models, GPU use or training. Raw Phase 1 is included to preserve grouping metadata needed for later deduplication and joins. Leave at least 6 GiB disk free; the downloader caps each file at 2 GiB and records failures. Network duration depends on file sizes and bandwidth. No added Python packages or sudo needed.

```bash
cd ~/cad_project
git pull --ff-only origin main &&
python3 scripts/download_llmail_phase1.py \
  --output-dir data/external/llmail_phase1_v1
```

Then copy only the small summary:

```bash
cp ~/cad_project/data/external/llmail_phase1_v1/intake_summary.json \
  ~/Desktop/llmail_phase1_intake_summary.json
```

Upload `llmail_phase1_intake_summary.json`, including if a download fails. Keep source payload files local; do not commit them or upload a multi-gigabyte archive. If a retry is needed, preserve the failed summary and use a new output directory.

After schema verification, define joins, label policy, length handling, grouped splits and near-duplicate controls before any fitting. MiniLM's token limit needs explicit handling; do not silently truncate emails. This data is competition-sourced in a simulated workflow, not production incident telemetry. No v3 efficacy or security improvement has yet been measured.
