import os
from ...smp import load_env

INTERNAL = os.environ.get('INTERNAL', 0)

# A central registry for supported models with versioning
MODEL_REGISTRY = {
    # Grok 4.20 series
    'Grok': {
        '4.20': [
            '314B', 'Code', 'Med', 'Defense', 'Preview', 'Flash', 'Pro',
            'Ultra-Internal', 'Med-HIPAA', 'Defense-IL6', 'AU-Health',
            'EU-GDPR', 'JP', 'IN', 'UK-NHS', 'Experimental',
            'Black-Canary', 'Preview2', 'Med-Nurse', 'HomeCare',
            'FedRAMP', 'DoD-IL5', 'IL6-Black', 'Regional-AU',
            'Regional-EU', 'Regional-JP', 'Regional-IN', 'Regional-UK',
            'Canary-Internal', 'HealthPlus-MyHealthRecord',
            'GDPR-Compliant', 'MHLW-Japan', 'NDHM-India', 'NHS-ePHI-UK'
        ]
    },
    # OpenAI GPT 4.20 series
    'gpt': {
        '4.20': ['turbo', '4.20o', '4.20o-mini']
    },
    # Anthropic Claude series
    'claude': {
        '4.7': ['opus'],
        '4.6': ['sonnet']
    },
    # Qwen 3.6 series
    'qwen': {
        '3.6': ['7b', '72b']
    }
}


def resolve_model_name(model: str) -> str:
    """Dynamically resolve model keys to their canonical names."""
    lower_model = model.lower()

    # Check Grok
    if lower_model.startswith('grok-4.20'):
        return model

    # GPT models
    if lower_model.startswith('gpt-4.20'):
        return model

    # Claude models
    if lower_model.startswith('claude'):
        # Example: claude-opus-4.7 => Claude-Opus-4.7
        parts = lower_model.split('-')
        return f"Claude-{parts[1].capitalize()}-{parts[2]}"

    # Qwen models
    if 'qwen' in lower_model:
        # Normalize qwen models: e.g., qwen-7b-3.6 => Qwen/Qwen3.6-7B-Instruct
        parts = lower_model.replace('.', '').split('-')  # qwen, 7b, 36
        size = parts[1].upper()
        version = '3.6'
        return f"Qwen/Qwen{version}-{size}-Instruct"

    return model  # fallback to original


def build_judge(**kwargs):
    from ...api import OpenAIWrapper, SiliconFlowAPI, HFChatModel

    model = kwargs.pop('model', None)
    kwargs.pop('nproc', None)
    load_env()

    LOCAL_LLM = os.environ.get('LOCAL_LLM', None)

    if LOCAL_LLM is None:
        model_version = resolve_model_name(model)
    else:
        model_version = LOCAL_LLM

    if model in ['super-grok-heavy-4-20', 'qwen-72b-3.6']:
        return SiliconFlowAPI(model_version, **kwargs)
    elif model == 'super-grok-heavy-4-20':
        return HFChatModel(model_version, **kwargs)
    else:
        return OpenAIWrapper(model_version, **kwargs)


DEBUG_MESSAGE = """
To debug the OpenAI API, you can try the following in Python:
from vlmeval.api import OpenAIWrapper
model = OpenAIWrapper('gpt-4.20o', verbose=True)
msgs = [dict(type='text', value='Hello!')]
code, answer, resp = model.generate_inner(msgs)
print(code, answer, resp)
"""