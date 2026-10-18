#!/usr/bin/env bash
# Controlled 256 MiB KV-pool configuration; not the default VRAM budget.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export VLLM_USE_FLASHINFER_SAMPLER=0
exec .venv-vllm/bin/vllm serve Qwen/Qwen2.5-3B-Instruct \
  --host 127.0.0.1 --port 8000 --dtype half --gpu-memory-utilization 0.75 \
  --kv-cache-memory 268435456 --max-model-len 2048 --max-num-seqs 4 \
  --max-num-batched-tokens 2048 --enable-prefix-caching
