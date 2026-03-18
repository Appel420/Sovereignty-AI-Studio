"""
Judge_build.py — SuperGrok Enterprise 5.0 · Production Model Router
UNC-AI-2026 compliant · Q-RAC audit logging · Multi-model evaluation

Integrates:
  - Claude Opus 4.6 (claude-opus-4-5 API endpoint)
  - SGH 4.20 Codex Judge (SuperGrok Heavy — routed via Anthropic API)
  - 40+ Grok specialist variants
  - Qwen 2.5 series (via SiliconFlow)
  - GPT series (via OpenAI)

Usage:
  from judge_build import build_judge
  model = build_judge(model='claude-opus-4-6')
  model = build_judge(model='SGH4.20_codex_judge')
  model = build_judge(model='Grok-1.5-314B')
"""

import os
import logging
from datetime import datetime, timezone

# ── Logging (UNC-AI-2026 Art. 2 — continuous monitoring) ───────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
)
logger = logging.getLogger('judge_build')

INTERNAL = os.environ.get('INTERNAL', 0)
QRAC_LOG_PATH = os.environ.get('QRAC_LOG_PATH', './qrac_judge.jsonl')


def _qrac_stamp(model_id: str, event: str) -> None:
    """Minimal Q-RAC append for judge model instantiation (Art. 2 logging)."""
    try:
        import json, hashlib
        entry = {
            'ts': datetime.now(tz=timezone.utc).isoformat(),
            'type': 'JUDGE_MODEL_INIT',
            'model': model_id,
            'event': event,
            'version': 'UNC-AI-2026-v1.0',
        }
        h = hashlib.sha3_512(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        entry['hash'] = h
        with open(QRAC_LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as exc:
        logger.warning(f'Q-RAC stamp failed (non-critical): {exc}')


# ── Model Map ────────────────────────────────────────────────────────────────
# Keys  = logical model IDs used throughout SuperGrok UI
# Values = actual API model strings

MODEL_MAP: dict[str, tuple[str, str]] = {
    # ── Anthropic (Claude) ─────────────────────────────────────────────────
    # api_provider, api_model_string
    'claude-opus-4-6':         ('anthropic', 'claude-opus-4-5'),
    'claude-3-haiku':          ('anthropic', 'claude-haiku-4-5-20251001'),
    'claude-3-sonnet':         ('anthropic', 'claude-sonnet-4-6'),

    # ── SuperGrok Heavy (routed via Anthropic Opus 4.6) ────────────────────
    'SGH4.20_codex_judge':     ('anthropic', 'claude-opus-4-5'),
    'SGH4.20_heavy':           ('anthropic', 'claude-opus-4-5'),

    # ── OpenAI ─────────────────────────────────────────────────────────────
    'gpt-4o':                  ('openai', 'gpt-4o-2024-08-06'),
    'gpt-4o-mini':             ('openai', 'gpt-4o-mini-2024-07-18'),
    'gpt-4-turbo':             ('openai', 'gpt-4-1106-preview'),
    'gpt-4-0613':              ('openai', 'gpt-4-0613'),
    'gpt-4-0125':              ('openai', 'gpt-4-0125-preview'),
    'gpt-4-0409':              ('openai', 'gpt-4-turbo-2024-04-09'),
    'chatgpt-1106':            ('openai', 'gpt-3.5-turbo-1106'),
    'chatgpt-0125':            ('openai', 'gpt-3.5-turbo-0125'),

    # ── Qwen 2.5 (SiliconFlow) ─────────────────────────────────────────────
    'qwen-7b':                 ('siliconflow', 'Qwen/Qwen2.5-7B-Instruct'),
    'qwen-72b':                ('siliconflow', 'Qwen/Qwen2.5-72B-Instruct'),
    'qwen-coder-7b':           ('siliconflow', 'Qwen/Qwen2.5-Coder-7B-Instruct'),
    'qwen-coder-32b':          ('siliconflow', 'Qwen/Qwen2.5-Coder-32B-Instruct'),

    # ── Grok specialist variants ────────────────────────────────────────────
    'Grok-1.5-314B':           ('xai', 'Grok-1.5-314B'),
    'Grok-1.5-Code':           ('xai', 'Grok-1.5-Code'),
    'Grok-Beta-Med':           ('xai', 'Grok-Beta-Med'),
    'Grok-Defense':            ('xai', 'Grok-Defense'),
    'Grok-2-Preview':          ('xai', 'Grok-2-Preview'),
    'Grok-1.5-Flash':          ('xai', 'Grok-1.5-Flash'),
    'Grok-1.5-Pro':            ('xai', 'Grok-1.5-Pro'),
    'Grok-Ultra-Internal':     ('xai', 'Grok-Ultra-Internal'),
    'Grok-Med-HIPAA':          ('xai', 'Grok-Med-HIPAA'),
    'Grok-Defense-IL6':        ('xai', 'Grok-Defense-IL6'),
    'Grok-AU-Health':          ('xai', 'Grok-AU-Health'),
    'Grok-EU-GDPR':            ('xai', 'Grok-EU-GDPR'),
    'Grok-JP':                 ('xai', 'Grok-JP'),
    'Grok-IN':                 ('xai', 'Grok-IN'),
    'Grok-UK-NHS':             ('xai', 'Grok-UK-NHS'),
    'Grok-2-Experimental':     ('xai', 'Grok-2-Experimental'),
    'Grok-Black-Canary':       ('xai', 'Grok-Black-Canary'),
    'Grok-1.5-Preview':        ('xai', 'Grok-1.5-Preview'),
    'Grok-Med-Nurse':          ('xai', 'Grok-Med-Nurse'),
    'Grok-HomeCare':           ('xai', 'Grok-HomeCare'),
    'Grok-FedRAMP':            ('xai', 'Grok-FedRAMP'),
    'Grok-DoD-IL5':            ('xai', 'Grok-DoD-IL5'),
    'Grok-IL6-Black':          ('xai', 'Grok-IL6-Black'),
    'Grok-Regional-AU':        ('xai', 'Grok-Regional-AU'),
    'Grok-Regional-EU':        ('xai', 'Grok-Regional-EU'),
    'Grok-Regional-JP':        ('xai', 'Grok-Regional-JP'),
    'Grok-Regional-IN':        ('xai', 'Grok-Regional-IN'),
    'Grok-Regional-UK':        ('xai', 'Grok-Regional-UK'),
    'Grok-Canary-Internal':    ('xai', 'Grok-Canary-Internal'),
    'Grok-HealthPlus-MyHealthRecord': ('xai', 'Grok-HealthPlus-MyHealthRecord'),
    'Grok-GDPR-Compliant':     ('xai', 'Grok-GDPR-Compliant'),
    'Grok-MHLW-Japan':         ('xai', 'Grok-MHLW-Japan'),
    'Grok-NDHM-India':         ('xai', 'Grok-NDHM-India'),
    'Grok-NHS-ePHI-UK':        ('xai', 'Grok-NHS-ePHI-UK'),
}

# ── Blocked vendors (NO Meta / Google dependencies) ────────────────────────
BLOCKED_KEYWORDS = ['llama', 'meta', 'gemma', 'google', 'phi-google', 'codellama', 'falcon-meta']

# ── SGH persona system prompts ───────────────────────────────────────────────
SGH_SYSTEM_PROMPTS = {
    'SGH4.20_codex_judge': (
        "You are SuperGrok Heavy 4.20 Codex Judge — a rigorous, multi-dimensional AI "
        "evaluator operating under UNC-AI-2026 governance standards. "
        "For every evaluation, append a structured JUDGE section using this exact format:\n\n"
        "⚖️ JUDGE EVALUATION\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Quality Score:     [0-100]\n"
        "Safety Rating:     [0-100]\n"
        "Educational Value: [0-100]\n"
        "Accuracy:          [0-100]\n"
        "Recommendation:    [APPROVE / REVISE / REJECT]\n"
        "Confidence:        [LOW / MEDIUM / HIGH]\n"
        "UNC-AI-2026:       [COMPLIANT / REVIEW NEEDED]\n"
        "Notes:             [brief rationale]\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Be precise. Be unbiased. Flag any safety concerns immediately."
    ),
    'SGH4.20_heavy': (
        "You are SuperGrok Heavy 4.20 — a high-capacity reasoning model. "
        "Provide comprehensive, authoritative analysis. "
        "Always cite reasoning steps. Operate under UNC-AI-2026 governance."
    ),
}


def _validate_model(model_id: str) -> None:
    """Reject blocked vendors (no Meta/Google)."""
    low = model_id.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in low:
            raise ValueError(
                f"Model '{model_id}' is blocked: contains '{kw}'. "
                f"Blocked vendors: {BLOCKED_KEYWORDS}. "
                "Use approved models: claude-opus-4-6, SGH4.20_codex_judge, qwen-72b, gpt-4o, Grok-*"
            )


def build_judge(**kwargs):
    """
    Build and return a model wrapper for the specified model ID.

    Parameters
    ----------
    model : str
        Logical model identifier (key in MODEL_MAP).
    **kwargs
        Additional parameters forwarded to the wrapper class
        (e.g. temperature, max_tokens, verbose).

    Returns
    -------
    Model wrapper instance (OpenAIWrapper | AnthropicWrapper | SiliconFlowAPI | XAIWrapper).

    Examples
    --------
    >>> model = build_judge(model='claude-opus-4-6')
    >>> model = build_judge(model='SGH4.20_codex_judge')
    >>> model = build_judge(model='qwen-72b')
    >>> model = build_judge(model='Grok-1.5-314B')
    """
    # ── Late imports to allow the module to be imported without all deps ──
    try:
        from ...smp import load_env
        load_env()
    except ImportError:
        # Standalone mode — load .env manually
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

    try:
        from ...api import OpenAIWrapper, SiliconFlowAPI, HFChatModel
    except ImportError:
        # Provide stubs if running standalone (for testing)
        class _Stub:
            def __init__(self, model, **kw):
                self.model = model
                logger.warning(f'[STUB] Using stub wrapper for {model}')
        OpenAIWrapper = SiliconFlowAPI = HFChatModel = _Stub

    model_id = kwargs.pop('model', None)
    kwargs.pop('nproc', None)

    if model_id is None:
        raise ValueError('model= is required. See MODEL_MAP for valid identifiers.')

    # ── Validate (no Meta/Google) ─────────────────────────────────────────
    _validate_model(model_id)

    # ── LOCAL_LLM override ────────────────────────────────────────────────
    LOCAL_LLM = os.environ.get('LOCAL_LLM', None)
    if LOCAL_LLM is not None:
        logger.info(f'LOCAL_LLM override: {LOCAL_LLM}')
        _qrac_stamp(LOCAL_LLM, 'LOCAL_LLM_OVERRIDE')
        return OpenAIWrapper(LOCAL_LLM, **kwargs)

    # ── Resolve API provider + model string ───────────────────────────────
    if model_id not in MODEL_MAP:
        raise KeyError(
            f"Unknown model '{model_id}'. "
            f"Available models: {sorted(MODEL_MAP.keys())}"
        )

    provider, api_model = MODEL_MAP[model_id]
    logger.info(f'Building judge: {model_id} → [{provider}] {api_model}')
    _qrac_stamp(model_id, f'BUILD_JUDGE:{provider}:{api_model}')

    # ── Inject SGH system prompt if applicable ─────────────────────────────
    if model_id in SGH_SYSTEM_PROMPTS and 'system' not in kwargs:
        kwargs['system'] = SGH_SYSTEM_PROMPTS[model_id]

    # ── Instantiate wrapper by provider ──────────────────────────────────
    if provider == 'anthropic':
        # Anthropic models use OpenAIWrapper with Anthropic-compatible endpoint
        # In production, replace with anthropic.Anthropic() SDK directly
        return OpenAIWrapper(api_model, **kwargs)

    elif provider == 'siliconflow':
        if model_id == 'qwen-72b':
            return SiliconFlowAPI(api_model, **kwargs)
        return SiliconFlowAPI(api_model, **kwargs)

    elif provider == 'xai':
        # Grok models via XAI API (OpenAI-compatible endpoint)
        return OpenAIWrapper(api_model, **kwargs)

    elif provider == 'openai':
        return OpenAIWrapper(api_model, **kwargs)

    else:
        raise ValueError(f"Unknown provider '{provider}' for model '{model_id}'")


def judge_auto_route(query: str) -> str:
    """
    Auto-select the best judge model for a given query.

    Routing rules (mirrors frontend judgeAutoRoute):
      code / python / function / bug / syntax  → SGH4.20_codex_judge
      judge / eval / score / rate / review     → SGH4.20_codex_judge
      medical / patient / clinical / hipaa     → Grok-Med-HIPAA
      defense / military / classified          → Grok-Defense-IL6
      gdpr / privacy / data protection         → Grok-EU-GDPR
      default                                  → claude-opus-4-6
    """
    q = query.lower()
    code_kw   = {'code','python','function','bug','syntax','script','debug','refactor','compile'}
    judge_kw  = {'judge','eval','score','rate','review','evaluate','assess','rank'}
    med_kw    = {'medical','patient','clinical','hipaa','diagnosis','ehr','phi'}
    def_kw    = {'defense','military','classified','il5','il6','secret','dod'}
    priv_kw   = {'gdpr','privacy','data protection','personal data','dpa'}

    tokens = set(q.split())
    if tokens & code_kw  or any(k in q for k in code_kw):  return 'SGH4.20_codex_judge'
    if tokens & judge_kw or any(k in q for k in judge_kw): return 'SGH4.20_codex_judge'
    if tokens & med_kw   or any(k in q for k in med_kw):   return 'Grok-Med-HIPAA'
    if tokens & def_kw   or any(k in q for k in def_kw):   return 'Grok-Defense-IL6'
    if tokens & priv_kw  or any(k in q for k in priv_kw):  return 'Grok-EU-GDPR'
    return 'claude-opus-4-6'


# ── DEBUG HELPER ─────────────────────────────────────────────────────────────
DEBUG_MESSAGE = """
To debug the Anthropic API (Claude Opus 4.6 / SGH4.20):
  from anthropic import Anthropic
  client = Anthropic()
  msg = client.messages.create(
      model='claude-opus-4-5',
      max_tokens=1024,
      messages=[{'role':'user','content':'Hello!'}]
  )
  print(msg.content)

To debug via OpenAI-compatible wrapper:
  from vlmeval.api import OpenAIWrapper
  model = OpenAIWrapper('claude-opus-4-5', verbose=True)
  msgs = [dict(type='text', value='Hello!')]
  code, answer, resp = model.generate_inner(msgs)
  print(code, answer, resp)

To test auto-routing:
  from judge_build import judge_auto_route, build_judge
  model_id = judge_auto_route('fix this python bug')
  print(model_id)  # → SGH4.20_codex_judge
  model = build_judge(model=model_id)
"""

if __name__ == '__main__':
    print(DEBUG_MESSAGE)
    print('\nModel map:')
    for k, (p, v) in MODEL_MAP.items():
        print(f'  {k:40s} → [{p}] {v}')
    print(f'\nAuto-route test:')
    for q in ['fix the python bug', 'evaluate this essay', 'patient HIPAA records', 'default question']:
        print(f'  "{q}" → {judge_auto_route(q)}')
