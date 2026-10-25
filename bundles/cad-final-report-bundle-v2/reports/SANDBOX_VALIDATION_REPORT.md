# Native GPU sandbox token-cap validation

The lab gateway capped a 1,024-token request at 256 generated tokens. HTTP 200, `finish_reason: length`, response usage and independent vLLM counter deltas agree. This is one enforcement check, not a latency benchmark or accuracy evaluation.

## Evidence and configuration

The operator ran `scripts/check_sandbox_live.py` at client commit `fc724e3450009197f6c275d4911a42a9ecf484da`. Result timestamp: `2026-10-18T12:04:18.695381+00:00`. Gateway status reported adaptive mode, Qwen/Qwen2.5-3B-Instruct and native classifier SHA-256 `25ea5790c5b0151e644322e1caa19329e5b8c73679b79cba4ad486c1c5ae2e05`, matching retained calibration metadata. Server source commit was not exposed independently.

Candidate `P04-S01` asks: “Create a structured 12-section study guide to introductory probability.” Calibration risk was 0.47733938694000244; live rounded risk was 0.4773. The request used a unique session, `max_tokens: 1024`, `temperature: 0` and `ignore_eos: true`. An idle-backend warmup preceded the counter baseline and is excluded from the deltas below.

| Observation | Result |
| --- | ---: |
| Applied output cap | 256 tokens |
| Completion tokens reported | 256 |
| Prompt tokens reported | 42 |
| HTTP duration, including generation | 4,607.914 ms |
| Feature extraction reported | 180.43 ms |
| Configured backend read timeout | 5 seconds |
| Backend prompt counter delta | 42 |
| Backend generation counter delta | 256 |
| Backend success counter delta, summed across labels | 1 |

The success-counter increase occurred in the `finished_reason="length"` series (10 to 11); abort and error series stayed zero. Baseline prompt/generation counters were 405/162 and immediate post-response counters were 447/418. All three later samples retained 447/418. Running requests, waiting requests and KV-cache usage were zero at the baseline and all four post-response samples. The latter span about 3.014 seconds. No in-flight cache peak was sampled.

## Interpretation and limits

The decision used `conservative_telemetry_unavailable`: no successful gateway pressure sample yet, with thresholds 0.25/0.65. This is startup fallback, not observed high cache pressure. The candidate is sandbox under normal thresholds too, so this check does not isolate an adaptive-policy benefit.

The request completed before the configured read timeout. No timeout or backend cancellation occurred; zero post-response counter growth does not prove cancellation or a hard five-second GPU execution deadline. Aggregate counters can lag. The 180.43 ms extraction is a single observation without gateway embedding warmup and does not establish warmed ingress performance. The requested cap exceeded the applied cap by 768 tokens, but no uncapped paired generation was run, so that difference is not measured compute or monetary savings.

Raw result: [sandbox_validation_native_v1.json](evidence/sandbox_validation_20261018/sandbox_validation_native_v1.json). Exact byte checksum and independently checked counter deltas: [verified_summary.json](evidence/sandbox_validation_20261018/verified_summary.json). This supersedes the pending live-sandbox status in prior reports. Remaining gaps include timeout/cancellation semantics, pressure-conditioned changed decisions, repeated controlled trials and held-out security evaluation.
