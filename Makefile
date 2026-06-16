PYTHON ?= python3
PIP ?= pip3

.PHONY: py-lint py-test ci

py-lint:
	$(PYTHON) -m pylint backend src workflows AI_Eyes_Medical --ignore=external,Sovereignty_python-keycloak-master

py-test:
	$(PYTHON) -m pytest

ci:
	$(PYTHON) -m pip install torch pennylane numpy scipy scikit-learn pysubs2 ffmpeg-python mediapipe opencv-python redis python-jose passlib blake3 cryptography librosa libcst pyttsx3
	$(PYTHON) -m pylint backend src workflows AI_Eyes_Medical --ignore=external,Sovereignty_python-keycloak-master
	$(PYTHON) -m pytest
