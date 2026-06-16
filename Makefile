PYTHON ?= python3
PIP ?= pip3

.PHONY: py-lint py-test ci

PYLINT_TARGETS = backend workflows src/utils/cli.py src/utils/subtools.py
PYLINT_IGNORE = external,Sovereignty_python-keycloak-master,src/agents/eeg_agent_qresist.py,src/security/SecureApp.py,src/models/quantum_layer.py,src/utils/system_File_Log.py,src/utils/constance.py,src/agents/AI-Lie-Detector.py,src/agents/eeg_agent.py,src/agents/Coach_agent.py,src/agents/Second_Squad_Agent.py,src/agents/XAI-Judge.py,src/models/ML_Board.py,src/security/Voice_Guard.py,src/security/Syntax-Guard.py

py-lint:
	$(PYTHON) -m pylint $(PYLINT_TARGETS) --ignore=$(PYLINT_IGNORE)

py-test:
	$(PYTHON) -m pytest

ci:
	$(PYTHON) -m pip install torch pennylane numpy scipy scikit-learn pysubs2 ffmpeg-python mediapipe opencv-python redis python-jose passlib blake3 cryptography librosa libcst pyttsx3 argon2-cffi
	$(PYTHON) -m pylint $(PYLINT_TARGETS) --ignore=$(PYLINT_IGNORE)
	$(PYTHON) -m pytest
