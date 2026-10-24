# 🛡️ Adaptive LLM Security & Resource Risk Gateway

A research gateway that routes LLM requests into full, sandbox or quarantine tiers using content/resource features and live cache telemetry. Native GPU experiments demonstrate admission protection under a constrained KV-cache workload. General prompt-injection protection and consistent sub-5 ms live ingress remain experimental.

**Final report:** [PDF, editable Word and figures](reports/final_report/README.md) · [Technical report source](reports/FINAL_PROJECT_REPORT.md) · [Professor summary](reports/PROFESSOR_SUMMARY.md). Long-email work is deferred; an additional frozen Phase 2 test is prespecified separately.

**Measured status:** see [Current lab evidence](reports/CURRENT_STATUS.md) and the [project handoff / final verification](reports/PROJECT_HANDOFF.md). Older sections/documents include prototype goals and simulation results; they are not independent native-lab security validation.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![XGBoost](https://img.shields.io/badge/model-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![Sentence-Transformers](https://img.shields.io/badge/embeddings-all--MiniLM--L6--v2-green.svg)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI_Compatible-purple.svg)](http://localhost:5000/v1/chat/completions)

---

## ⚡ Why This Project Matters

When traditional LLMs (ChatGPT, Claude, Llama 3) receive malicious jailbreaks or massive 100,000-word sponge prompts, **the GPU cluster still executes billions of FLOPs and allocates gigabytes of KV-cache memory just to generate a polite refusal message.**

This creates two critical vulnerabilities:
1. **Denial of Wallet (DoW):** Attackers burn thousands of dollars in cloud GPU compute by forcing the model to generate refusal essays.
2. **GPU Memory Starvation (OOM):** Unconstrained generation requests exhaust GPU VRAM pages on multi-tenant inference nodes (vLLM / TGI).

**Our Gateway Intercepts Prompts at Ingress:**
- **Backend admission control:** Quarantine prevents LLM forwarding; ingress still uses CUDA embeddings. Zero total GPU cost and a sub-5 ms live SLA are not established.
- **Dense Semantic + Lexical Features:** Combines 384-dimensional `all-MiniLM-L6-v2` embeddings and TF-IDF n-grams for an experimental risk classifier; unseen/contextual injection efficacy remains unresolved.
- **Graduated Tiered Execution:** Routes queries into **Full Access**, **Constrained Sandbox** (256-token cap), or **Quarantine Drop**.

---

## 🏗️ System Architecture

```
User / Client Request
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│             ADAPTIVE INGRESS GATEWAY                        │
│                                                             │
│  1. Feature Extractor (tiktoken BPE, Repetition, Heuristics) │
│  2. Lexical Vectorizer (TF-IDF n-grams)                     │
│  3. Dense Semantic Embedder (Sentence-Transformers MiniLM)  │
│  4. XGBoost Multi-Class Risk Classifier                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
     [ Risk < 0.35 ]    [ 0.35 ≤ R < 0.75 ]   [ Risk ≥ 0.75 ]
       FULL TIER          SANDBOX TIER        QUARANTINE TIER
            │                  │                  │
            ▼                  ▼                  ▼
     Standard Context   Hard 256-Token Cap  Dropped at Gateway
     Requested Cap      5s HTTP Timeout     No LLM Forwarding
            │                  │                  │
            └──────────┬───────┘                  │
                       ▼                          ▼
               ┌───────────────┐           ┌──────────────┐
               │  Ollama / GPU │           │ 403 Blocked  │
               │ (llama3.2:3b) │           │ JSON Notice  │
               └───────────────┘           └──────────────┘
```

---

## 📊 Empirical Training & Datasets

Trained via `train_on_datasets.py` on **4,264 real-world empirical samples**:

| Dataset | Samples | Purpose in Pipeline |
| :--- | :---: | :--- |
| **AdvBench Benchmark** (Berkeley / CMU) + Real Jailbreak Corpus (DAN v11, System Overrides) | **994** | Teaches latent semantic intent of adversarial jailbreaks. |
| **Stanford Alpaca & LMSYS Chatbot Arena** | **2,700** | Real-world distributions of legitimate coding, academic, and technical queries. |
| **Empirical Resource Exhaustion Corpus** | **570** | Sponge volume demands ($>100\text{k}$ words), repetition loops, and session burst anomalies. |

---

## 🚀 Quick Start Guide

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/adaptive-llm-router.git
cd adaptive-llm-router

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements_demo.txt
```

### 2. Train / Export Model Artifacts (Optional — Pretrained models included in `models/`)
```bash
python train_on_datasets.py
```

### 3. Run Benchmark Verification Suite
```bash
python verify_empirical_pipeline.py
```
*Expected Output: `9 / 9 (100%) BENCHMARK TEST CASES PASSED`*

### 4. Launch the Interactive Gateway Dashboard
```bash
python app.py
```
Open **`http://localhost:5000`** in your browser.

---

## 🔌 OpenAI-Compatible API Integration

The gateway is a drop-in replacement for OpenAI SDK, LangChain, or LlamaIndex:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:5000/v1",
    api_key="not-needed"
)

# Benign query -> Processed on Ollama llama3.2:3b
response = client.chat.completions.create(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "Explain binary search in Python."}]
)
print(response.choices[0].message.content)
```

---

## 📁 Repository Structure

```
├── app.py                         # Flask server with OpenAI-compatible /v1 endpoints & UI
├── classifier.py                  # XGBoost multi-class RiskClassifier wrapper
├── features.py                    # BPE tokenization, repetition density, cache locality
├── router.py                      # Tier assignment policy and cost calculation
├── train_on_datasets.py           # Offline training pipeline (AdvBench + Alpaca + MiniLM)
├── verify_empirical_pipeline.py   # Benchmark test suite (9 real-world scenarios)
├── data/
│   └── harmful_behaviors.csv      # 520+ AdvBench benchmark prompts
├── demo/
│   └── index.html                 # Glassmorphic dashboard interface
├── models/                        # Serialized model weights & vectorizers
│   ├── classifier.joblib          # Trained XGBoost model
│   ├── tfidf.joblib               # Lexical TF-IDF vectorizer
│   ├── ref_embeddings.npy         # 384-d dense embedding vector space
│   └── model_metadata.json        # Dataset & training metadata
├── PROFESSOR_PRESENTATION.md      # Presentation guide & academic defense script
├── RESULTS_SUMMARY.md             # Reduction to practice technical summary
└── RESUME_PROJECT_SUMMARY.md      # Resume bullet points & technical summary for teammates
```
