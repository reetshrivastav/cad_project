# Final report bundle — evidence edition 2.0

25 October 2026. Start with [all reports/evidence](../README.md).

- [Complete PDF](Adaptive_LLM_Gateway_Final_Report.pdf): download with GitHub's Download raw file button.
- [Editable Word](Adaptive_LLM_Gateway_Final_Report.docx).
- [Professor summary PDF](Professor_Summary.pdf).
- [Canonical technical Markdown](../FINAL_PROJECT_REPORT.md).
- [Evidence index with SHA256](EVIDENCE_INDEX.csv).
- [Render validation](document_checks.json).
- [Figures and source hashes](figures/).

Includes GPU protection, realistic-data studies, long-email coverage/quality, completed Phase 2 content-only transfer, final software/live checks, opt-in tuning and explicit novelty/claim boundaries. Default serving embedding path remains unchanged unless `GATEWAY_EMBEDDING_MODE=direct` is supplied. Models are not retrained by report generation.

Reproduce figures with `MPLCONFIGDIR=/tmp/cad-mpl-cache python scripts/build_final_report_figures.py`. Rendering requires Pandoc/XeLaTeX; supplied PDFs need no lab installation. Full raw evidence remains at the indexed GitHub paths; large source email datasets remain lab-local.
