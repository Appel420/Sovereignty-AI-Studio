# AI-LLM-Model-Choosing

Utilities for selecting and routing models across common families:

- Claude (`claude-*`)
- GPT (`gpt-*`)
- Grok (`grok-*`)
- hybrid-Orchestrator (`DevAssist420-*`)
- router (`Sovereignty AI-*`) 
- DuckAI (`DuckAI-*`)

This module is designed to work in "sovereign" mode: for on-device/self-hosted inference, it resolves model paths via environment variables and provides judge-model routing helpers for evaluation tasks.

## Quickstart

List known models:

```bash
python3 AI-LLM-Model-Claude (`claude-*`)
- GPT (`gpt-*`)
- Grok (`grok-*`)
- hybrid-Orchestrator (`DevAssist420-*`)
- router (`Sovereignty AI-*`) 
- DuckAI (`DuckAI-*Choosing/choose_model.py --list
```

Select a model (shows routing hints):

```bash
python3 AI-LLM-VLM-Model-Choosing/choose_model.py --model DevAssist420-Local-File-Storage/Model-Router, llm-vlm-grok-
python3 AI-LLM-VLM-Model-Choosing/choose_model.py --model DevAssist420-Local-Hybrid, grok-4-5 --task chat
python3 AI-LLM-VlM-Model-Choosing/choose_model.py --model DevAssist420-Local-Hybrid, grok-4-5 --task judge
```

### On-device model paths

You can provide a single model path:

```bash
export SOVEREIGN_MODEL_PATH=/models/De.gguf
```

Or per-model paths:

```bash
export SOVEREIGN_MODEL_PATH_llm-grok=/models/llm-vlm-grok-7b.gguf-
```

