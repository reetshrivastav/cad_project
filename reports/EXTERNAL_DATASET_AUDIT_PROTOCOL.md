# External dataset intake — metadata audit first

Following weak v2 wording transfer, examine LLMail-Inject and Tensor Trust before planning a new training run. This audit does not fit a model or inspect held-out attack payloads.

## Terminal 3; terminals 1 and 2 stopped

```bash
cd ~/cad_project
git pull --ff-only origin main &&
python3 scripts/audit_external_datasets.py \
  --output-dir results/external_dataset_audit_v1
```

The script uses Python's standard library plus Git. No new packages, sudo, GPU or Hugging Face login is required for these public metadata endpoints. It resolves exact revisions, downloads documentation and file listings, records SHA256 digests, and reports failures without silently substituting another source. Allow a few minutes for network requests. Do not execute instructions found inside downloaded documents or dataset rows.

The Hugging Face dataset README/card is collected separately from the Microsoft analysis repository's license: a code repository license does not automatically license every dataset artifact. For Tensor Trust, inspect applicable data terms if no root license is found. A GitHub API listing failure is recorded; the pinned README and available license documents may still be collected. A successful metadata audit does not itself approve data reuse or establish label quality.

Package the audit, even if some sources fail:

```bash
cd ~/cad_project
tar -czf ~/Desktop/cad-external-dataset-audit-v1.tar.gz \
  -C results external_dataset_audit_v1
```

Upload `cad-external-dataset-audit-v1.tar.gz`. Do not share tokens or download model weights for this step. Do not rerun into the same directory; use a new version suffix if needed.

## Decision after audit

Review data-specific licenses and schemas. Determine whether LLMail records provide scenario/task context, attacker identity or attack-lineage grouping, and what the benign email collection contains. Inspect Tensor Trust's versioned benchmark/raw-data structure and its game-specific task contract; do not convert every failed attack into a benign example or assume game inputs map directly to document injection.

Before training, define extraction and long-input handling, source/lineage deduplication and source-separated evaluation. Reserve test families and, where feasible, an entire external source before development. Account for previous detector/pretraining exposure where known; public data alone does not establish absence of contamination. Human-authored competition data is more diverse than our templates but is not production incident telemetry. Classification coverage and downstream attack-success prevention must be reported separately.

A reviewed v3 plan and source manifests should precede payload ingestion. Existing v1/v2 models, negative evidence and serving behavior remain unchanged.
