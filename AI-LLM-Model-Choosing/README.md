# AI-LLM-Model-Choosing

Utilities for selecting and routing models across common families:

- Claude (`claude-*`)
- GPT (`gpt-*`)
- Grok (`grok-*`)
- Qwen (`qwen-*`)

This module is designed to work in "sovereign" mode: for on-device/self-hosted inference, it resolves model paths via environment variables and provides judge-model routing helpers for evaluation tasks.

## Quickstart

List known models:

```bash
python3 AI-LLM-Model-Choosing/choose_model.py --list
```

Select a model (shows routing hints):

```bash
python3 AI-LLM-Model-Choosing/choose_model.py --model qwen-7b
python3 AI-LLM-Model-Choosing/choose_model.py --model grok-4-3 --task chat
python3 AI-LLM-Model-Choosing/choose_model.py --model grok-4-3 --task judge
```

### On-device model paths

You can provide a single model path:

```bash
export SOVEREIGN_MODEL_PATH=/models/my-model.gguf
```

Or per-model paths:

```bash
export SOVEREIGN_MODEL_PATH_QWEN_7B=/models/qwen-7b.gguf
```

