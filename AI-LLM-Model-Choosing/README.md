# AI-LLM-Model-Choosing

Utilities for selecting and routing model identifiers across the supported model families.

Supported families in `ai_core.model_selection`:

- Claude (`claude-*`)
- GPT (`gpt-*`)
- Grok (`grok-*`)
- Qwen (`qwen-*`, normally local/self-hosted)
- SGH judge (`sgh-judge`)

The selector provides model-family/backend hints and optional local model-path resolution. It is a selection helper, not an authorization boundary. Policy and capability enforcement remain downstream.

## Quickstart

List known model IDs:

```bash
python3 AI-LLM-Model-Choosing/choose_model.py --list
```

Select a model for chat:

```bash
python3 AI-LLM-Model-Choosing/choose_model.py --model grok-4-3 --task chat
```

Select the configured judge model:

```bash
python3 AI-LLM-Model-Choosing/choose_model.py --model grok-4-3 --task judge
```

## On-device model paths

A single default local path can be supplied with:

```bash
export SOVEREIGN_MODEL_PATH=/models/model.gguf
```

A per-model path uses the sanitized model ID as the environment-variable suffix. For example:

```bash
export SOVEREIGN_MODEL_PATH_QWEN_7B=/models/qwen-7b.gguf
```

Only local/self-hosted model families resolve a local path. Cloud-family identifiers receive routing metadata and do not implicitly become local.

## Contract

`choose_model.py` calls `ai_core.model_selection.select_model()`. Unknown identifiers fail closed with `UnknownModelError`; the selector does not silently substitute an unrecognized provider or model.
