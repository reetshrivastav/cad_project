# Reviewer-supplied priority packet intake — 24 October 2026

Update: the corrected upload has now been processed. Twenty-four intact rows are accepted as reviewer-supplied development annotations; row 042, replaced with a placeholder, is excluded. The review cycle is closed. See [project handoff](PROJECT_HANDOFF.md); the pending instructions below document the earlier intake state.

The uploaded 25-row packet records reviewer `Reet` on every row, with 13 injection, six benign and six unclear labels and nonempty notes. All expected IDs and columns are present. These are reviewer-supplied judgments; independence/blinding is not established because prior AI reviews were available.

Input integrity did not pass: email text changed in rows 013, 014, 023, 042, 054 and 056 (full IDs begin `LLMAIL-REVIEW-`). Differences include mojibake in punctuation and Chinese characters. Four affected emails contain multilingual forged dialogue. A label on a garbled display cannot automatically be accepted as a review of the original multilingual text.

The [intake manifest](evidence/llmail_human_review_intake_20261024/intake_manifest.json) preserves upload/restored/original hashes, changed-field digests, supplied labels/notes and pending IDs without committing source payloads. The original upload remains unmodified. A downloadable restored CSV uses exactly the original task/email strings and preserves every submitted ID, label, reviewer and note. Both properties were verified after writing and rereading the CSV. No source-label overwrite, model refit, threshold change or test rescoring occurred.

## Required recheck

Open `llmail-priority-adjudication-human-restored.csv` with UTF-8 and columns imported as Text. Recheck IDs 013, 014, 023, 042, 054 and 056 against the restored text. Original 042 is already largely garbled; restoration does not imply its meaning has become clear. Keep `unclear` where context or decoding is insufficient. Preserve actual reviewer identity; do not treat assistant explanations as independent human verification.

Save and upload the rechecked CSV as UTF-8, retaining IDs/task/email exactly. Label/note changes are allowed when review of the restored content warrants them. A brief note confirming the six restored rows were rechecked supplies the missing confirmation; the passage of time or unchanged labels alone does not establish it. No terminal/GPU run is needed. Until then all 25 annotations remain provisional and do not enter model development artifacts.
