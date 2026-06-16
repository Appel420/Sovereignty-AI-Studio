PYTHON ?= python3
PIP ?= pip3

.PHONY: py-lint py-test ci

py-lint:
	$(PYTHON) -m pylint backend src workflows AI_Eyes_Medical --ignore=external,Sovereignty_python-keycloak-master

py-test:
	$(PYTHON) -m pytest

ci: py-lint py-test
