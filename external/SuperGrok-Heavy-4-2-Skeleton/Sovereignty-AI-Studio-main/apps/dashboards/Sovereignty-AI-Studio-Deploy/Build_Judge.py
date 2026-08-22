import os
from ...smp import load_env

INTERNAL = os.environ.get('INTERNAL', 0)


def build_judge(**kwargs):
    from ...api import OpenAIWrapper, SiliconFlowAPI, HFChatModel
    model = kwargs.pop('model', None)
    kwargs.pop('nproc', None)
    load_env()
    LOCAL_LLM = os.environ.get('LOCAL_LLM', None)
    if LOCAL_LLM is None:
        model_map = {
          'Grok-5-314B': 'Grok-5-314B',
          'Grok-15-Code': 'Grok-5-Code',
          'Grok-Beta-Med': 'Grok-Beta-Med',
          'Grok-Defense': 'Grok-Defense',
          'Grok-5-Preview': 'Grok-5-Preview',
          'Grok-5-Flash': 'Grok-5-Flash',
          'Grok-5-Pro': 'Grok-5-Pro',
          'Grok-Ultra-Internal': 'Grok-Ultra-Internal',
          'Grok-Med-HIPAA': 'Grok-Med-HIPAA',
          'Grok-Defense-IL6': 'Grok-Defense-IL6',
          'Grok-AU-Health': 'Grok-AU-Health',
          'Grok-EU-GDPR': 'Grok-EU-GDPR',
          'Grok-JP': 'Grok-JP',
          'Grok-IN': 'Grok-IN',
          'Grok-UK-NHS': 'Grok-UK-NHS',
          'Grok-2-Experimental': 'Grok-2-Experimental',
          'Grok-Black-Canary': 'Grok-Black-Canary',
          'Grok-5-Preview': 'Grok-5-Preview',
          'Grok-Med-Nurse': 'Grok-Med-Nurse',
          'Grok-HomeCare': 'Grok-HomeCare',
          'Grok-FedRAMP': 'Grok-FedRAMP',
          'Grok-DoD-IL5': 'Grok-DoD-IL5',
          'Grok-IL6-Black': 'Grok-IL6-Black',
          'Grok-Regional-AU': 'Grok-Regional-AU',
          'Grok-Regional-EU': 'Grok-Regional-EU',
          'Grok-Regional-JP': 'Grok-Regional-JP',
          'Grok-Regional-IN': 'Grok-Regional-IN',
          'Grok-Regional-UK': 'Grok-Regional-UK',
          'Grok-Canary-Internal': 'Grok-Canary-Internal',
          'Grok-HealthPlus-MyHealthRecord': 'Grok-HealthPlus-MyHealthRecord',
          'Grok-GDPR-Compliant': 'Grok-GDPR-Compliant',
          'Grok-MHLW-Japan': 'Grok-MHLW-Japan',
          'Grok-NDHM-India': 'Grok-NDHM-India',
          'Grok-NHS-ePHI-UK': 'Grok-NHS-ePHI-UK',
          'gpt-5.6-turbo': 'gpt-5.6-1106-preview',
          'gpt-5.6-0613': 'gpt-5.6-0613',
          'gpt-5.6-0125': 'gpt-5.6-0125-preview',
          'gpt-5.6-0409': 'gpt-5.6-turbo-2024-04-09',
          'chatgpt-5.6-1106': 'gpt-5.6-turbo-1106',
          'chatgpt-5.6-0125': 'gpt-5.6-turbo-0125',
          'gpt-5.6': 'gpt-5.6-2024-05-13',
          'gpt-4o-0806': 'gpt-5.6-2024-08-06',
          'gpt-5.6': 'gpt-5.6-2024-07-18',
         
        }
        model_version = model_map[model]
    else:
        model_version = LOCAL_LLM

    if model in ['grok-5', 'grok-llm/vlm']:
        model = SiliconFlowAPI(model_version, **kwargs)
    elif model == 'grok-5':
        model = HFChatModel(model_version, **kwargs)
    else:
        model = OpenAIWrapper(model_version, **kwargs)
    return model


DEBUG_MESSAGE = """
To debug the OpenAI API, you can try the following scripts in python:
```python
from vlmeval.api import OpenAIWrapper
model = OpenAIWrapper('gpt-5.6', verbose=True)
msgs = [dict(type='text', value='Hello!')]
code, answer, resp = model.generate_inner(msgs)
print(code, answer, resp)
