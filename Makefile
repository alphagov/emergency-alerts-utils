.DEFAULT_GOAL := help
SHELL := /bin/bash


.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: bootstrap
bootstrap: ## Build project
	pip3 install -r requirements.txt

.PHONY: test
test: ## Run tests
	flake8 .
	isort --check-only ./emergency_alerts_utils ./tests
	black --check .
	pytest -n auto
	python setup.py sdist

clean:
	rm -rf cache venv

.PHONY: fix-imports
fix-imports:
	isort ./emergency_alerts_utils ./tests

.PHONY: reset-version
reset-version:
	git fetch
	git checkout origin/main -- emergency_alerts_utils/version.py

.PHONY: version-major
version-major: reset-version ## Update the major version number
	./scripts/bump_version.py major

.PHONY: version-minor
version-minor: reset-version ## Update the minor version number
	./scripts/bump_version.py minor

.PHONY: version-patch
version-patch: reset-version ## Update the patch version number
	./scripts/bump_version.py patch

.PHONY: uninstall-packages
uninstall-packages:
	python -m pip uninstall emergency-alerts-utils -y
	python -m pip freeze | xargs python -m pip uninstall -y
