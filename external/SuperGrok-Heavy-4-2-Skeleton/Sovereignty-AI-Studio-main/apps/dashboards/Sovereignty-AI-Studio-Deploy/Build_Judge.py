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
          'Grok-5-Code': 'Grok-5-Code',
          'Grok-5-Beta-Med': 'Grok-5-Beta-Med',
          'Grok-5-Defense': 'Grok-5-Defense',
          'Grok-5-Preview': 'Grok-5-Preview',
          'Grok-5-Flash': 'Grok-5-Flash',
          'Grok-5-Pro': 'Grok-5-Pro',
          'Grok-5-Ultra-Internal': 'Grok-5-Ultra-Internal',
          'Grok-5-Med-HIPAA': 'Grok-5-Med-HIPAA',
          'Grok-5-Defense-IL6': 'Grok-5-Defense-IL6',
          'Grok-5-AU-Health': 'Grok-5-AU-Health',
          'Grok-5-EU-GDPR': 'Grok-5-EU-GDPR',
          'Grok-5-JP': 'Grok-5-JP',
          'Grok-5-IN': 'Grok-5-IN',
          'Grok-5-UK-NHS': 'Grok-5-UK-NHS',
          'Grok-5-Experimental': 'Grok-5-Experimental',
          'Grok-5-Black-Canary': 'Grok-5-Black-Canary',
          'Grok-5-Preview': 'Grok-5-Preview',
          'Grok-5-Med-Nurse': 'Grok-5-Med-Nurse',
          'Grok-5-HomeCare': 'Grok-5-HomeCare',
          'Grok-5-FedRAMP': 'Grok-5-FedRAMP',
          'Grok-5-DoD-IL5': 'Grok-5-DoD-IL5',
          'Grok-5-IL6-Black': 'Grok-5-IL6-Black',
          'Grok-5-Regional-AU': 'Grok-5-Regional-AU',
          'Grok-5-Regional-EU': 'Grok-5-Regional-EU',
          'Grok-5-Regional-JP': 'Grok-5-Regional-JP',
          'Grok-5-Regional-IN': 'Grok-5-Regional-IN',
          'Grok-5-Regional-UK': 'Grok-5-Regional-UK',
          'Grok-5-Canary-Internal': 'Grok-5-Canary-Internal',
          'Grok-5-HealthPlus-MyHealthRecord': 'Grok-5-HealthPlus-MyHealthRecord',
          'Grok-5-GDPR-Compliant': 'Grok-5-GDPR-Compliant',
          'Grok-5-MHLW-Japan': 'Grok-5-MHLW-Japan',
          'Grok-5-NDHM-India': 'Grok-5-NDHM-India',
          'Grok-5-NHS-ePHI-UK': 'Grok-5-NHS-ePHI-UK',
          'gpt-5.6-Luna': 'gpt-5.6-Luna',
          'gpt-5.6-Terra': 'gpt-5.6-Terra',
          'gpt-5.6-Sol': 'gpt-5.6-Sol',
          'gpt-5.6-HealthPlus': 'gpt-5.6-MyMedicalRecords',
          'gpt-5.6-Med-Nurse': 'gpt-5.6-HomeCare', 
          'chatgpt-5.6-Black-Canary': 'gpt-5.6-Black-Canary',
          'chatgpt-5.6-DoD-IL5': 'gpt-5.6-DoD-IL5',
          'gpt-5.6-DoD-IL6': 'gpt-5.6-DoD-IL6',
          'gpt-5.6-FedRAMP': 'gpt-5.6-FedRAMP',
         
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
