PYTHON ?= python3
PIP ?= pip3
PYLINT ?= $(PYTHON) -m pylint
FIG_DIR ?= figures
FIG_PREFIX ?= demo

.PHONY: py-lint py-test figures clean ci

PYLINT_TARGETS = backend workflows src/utils/cli.py src/utils/subtools.py
PYLINT_IGNORE_PATHS = external,src/agents/eeg_agent_qresist.py,src/security/SecureApp.py,src/models/quantum_layer.py,src/utils/system_File_Log.py,src/utils/constance.py,src/agents/AI-Lie-Detector.py,src/agents/eeg_agent.py,src/agents/Coach_agent.py,src/agents/Second_Squad_Agent.py,src/agents/XAI-Judge.py,src/models/ML_Board.py,src/security/Voice_Guard.py,src/security/Syntax-Guard.py

py-lint:
	@command -v "$(PYTHON)" >/dev/null 2>&1 || { echo "Python runtime not found: $(PYTHON)" >&2; exit 1; }
	@$(PYLINT) $(PYLINT_TARGETS) --ignore-paths="$(PYLINT_IGNORE_PATHS)"

py-test:
	$(PYTHON) -m pytest

figures:
	$(PYTHON) -m pip install -e .
	sovereignty-figures --out-dir $(FIG_DIR) --prefix $(FIG_PREFIX)

clean:
	rm -rf $(FIG_DIR)

ci: py-lint py-test
