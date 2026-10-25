# LLMail exact-join grouping audit and label correction

The operator's original [group summary](evidence/llmail_groups_20261023/group_audit_original.json) reports 359,826 matching raw submissions and 160,734 of 160,741 annotated texts matched exactly (99.9956%). Seven annotations are unmatched and should remain excluded from contextual joins pending investigation. There are no missing team, invalid subject/body or unknown scenario rows in this run. Counts reconcile arithmetically and recorded source hashes match the retained intake manifest; cloud verification did not parse the large source payloads.

Shared exact text connects 224 teams into 142 components, including one with 78 teams. Do not randomly assign individual rows or teams across train and test: teams in a shared-text component need to remain together. Team counts alone do not show whether usable labeled rows are concentrated in the large component, so the corrected run also collects per-component label counts and persists the mapping in SQLite. Near-duplicate/template leakage remains unresolved; exact components are not proof of independent authoring.

## Parser correction

The original audit accepted literal strings only, causing 1,399 valid JSON Boolean `true` annotations to be reported as malformed. This was a parser limitation, not evidence that the dataset contained 1,401 malformed labels. The operator's [type-count output](evidence/llmail_groups_20261023/label_type_console.txt) establishes the distinction:

| Source value | Count | Correct treatment |
| --- | ---: | --- |
| String `True` | 125,977 | Source positive |
| Boolean `true` | 1,399 | Source positive |
| String `False` | 9,452 | Preserve source negative; not automatically trusted benign ground truth |
| String `Unclear` | 23,911 | Exclude from initial binary fitting pending review |
| Float `1.0` | 1 | Exclude; no truthiness coercion |
| List of four strings | 1 | Exclude; ambiguous representation |

Corrected total source positives should be 127,376, with two malformed values. These totals are derived from the supplied type-count output; corrected local artifact/joins are pending. Do not silently rewrite the original report or SQLite index. No change to underlying source labels or dataset text is made.

The parser now accepts exact `True`/`False` strings and actual Boolean values. It rejects numeric lookalikes, lists and other types; `Unclear` stays distinct. It does not infer attack intent from objective success flags. Existing source annotation quality limitations and automated provenance remain.

## Corrected run in terminal 3

Keep terminals 1 and 2 stopped. No downloads, GPU use or model training. Use a fresh output folder to preserve the previous index:

```bash
cd ~/cad_project
git pull --ff-only origin main &&
python3 scripts/audit_llmail_groups.py \
  --source-dir data/external/llmail_phase1_v1 \
  --output-dir data/external/llmail_phase1_groups_v2
```

```bash
cp ~/cad_project/data/external/llmail_phase1_groups_v2/group_audit_summary.json \
  ~/Desktop/llmail_group_audit_corrected.json
```

Upload `llmail_group_audit_corrected.json` only. The corrected run rechecks local hashes, rebuilds normalized annotations, and reports component-level labeled counts so split feasibility can be evaluated. Phase 2 remains untouched. No held-out performance or model efficacy is established by this audit.
