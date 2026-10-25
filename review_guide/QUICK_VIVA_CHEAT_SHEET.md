# ⚡ Quick Viva Cheat Sheet (Scan 5 Mins Before Review)
**Project:** Adaptive Ingress Admission Control for Multi-Tenant LLM Serving  
**Authors:** Reet Shrivastav, Pranshi Gupta, Anushka Thakur

---

### 1. The Core Idea (1 Sentence)
*"We built an upfront network gateway that intercepts prompts in under 20 ms, calculates a multi-factor risk score, and quarantines volumetric memory-exhaustion attacks before they can saturate the GPU's KV-cache and stall innocent users."*

---

### 2. The Golden Numbers (Hardware Benchmark on RTX A4000)
| Metric | Without Gateway (Direct vLLM) | With Gateway (Our System) |
| :--- | :---: | :---: |
| **Normal User Latency (Benign Probe)** | **50.24 seconds** 🐢 | **0.30 seconds (300 ms)** ⚡ |
| **GPU KV-Cache Occupancy** | **100% (Completely Saturated)** | **0.88% (Virtually Free)** |
| **Requests Waiting in Queue** | **11 to 12 requests** | **0 requests** |
| **Wasted Backend Generation Tokens** | 14,464 tokens generated | **43,008 tokens avoided** |
| **Attack Demands Quarantined** | 0 / 24 blocked | **24 / 24 (100% blocked)** |

---

### 3. The 6 Ingress Features Extracted in < 20 ms
1. **Token Length ($n_{\text{tokens}}$):** Byte-Pair Encoding count using `tiktoken` (0.2 ms).
2. **Lexical Matching ($s_{\text{lexical}}$):** Character/word TF-IDF similarity against known jailbreak phrases (0.45 ms).
3. **Dense Semantic Matching ($s_{\text{semantic}}$):** 384-d `all-MiniLM-L6-v2` embedding on CUDA FP16 (2.1 ms).
4. **Repetition Density ($r_{\text{repeat}}$):** Bigram loop ratio to detect infinite sponge cycles.
5. **Output Demand Heuristic ($d_{\text{output}}$):** Detects phrases like *"write 100,000 words"*, *"50 chapters"*.
6. **Session Burst Count ($c_{\text{session}}$):** Prefix repetition counter to detect high-frequency burst floods.

---

### 4. The Three Tiers (Graduated Action)
* **Risk Formula:** $\text{Risk } R = 1 - P(\text{benign})$ using multi-class **XGBoost**.
* **Full Tier ($R < 0.35$):** Safe requests $\rightarrow$ Uncapped output and standard context.
* **Sandbox Tier ($0.35 \le R < 0.75$):** Borderline requests $\rightarrow$ Hard **256-token cap** and **5.0-second timeout**.
* **Quarantine Tier ($R \ge 0.75$):** Malicious requests $\rightarrow$ **HTTP 403 Forbidden** at proxy layer ($0.00 GPU compute).

---

### 5. Four Critical "Gotchas" Reviewers Love to Ask:
1. **"Why 256 MiB KV-Pool?"**  
   $\rightarrow$ On a full 16 GB GPU, saturation testing takes 6–10 hours per run. The 256 MiB pool (455 blocks, 7,280 tokens) created a mathematically controlled, reproducible microcosm where memory dynamics happen in minutes across 9 balanced blocks.
2. **"Why didn't `nvidia-smi` show 0 MB VRAM?"**  
   $\rightarrow$ vLLM preallocates its memory arena (~7.4 GB) upon startup. The real physical metric of memory pressure is **active KV-cache block occupancy**, which dropped from 100% to 0.88%.
3. **"What did the LLMail-Inject test show?"**  
   $\rightarrow$ It proved that lightweight semantic embeddings **cannot solve contextual prompt injection** (dropping to 61% recall, and long-window pooling flagged 91% of innocent emails). Upfront filters protect GPU capacity, but injection requires execution sandboxing.
4. **"How did you optimize ingress speed?"**  
   $\rightarrow$ By bypassing high-level wrapper overhead with direct `torch.inference_mode()` on CUDA FP16, dropping live extraction latency from **24.62 ms down to 18.84 ms** (a 23.5% speedup).
