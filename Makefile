.DEFAULT_GOAL := help
SHELL := /bin/bash

NVM_VERSION := 0.39.7
NODE_VERSION := 16.14.0

write-source-file:
	@if [ -f ~/.zshrc ]; then \
		if [[ $$(cat ~/.zshrc | grep "export NVM") ]]; then \
			cat ~/.zshrc | grep "export NVM" | sed "s/export//" > ~/.nvm-source; \
		else \
			cat ~/.bashrc | grep "export NVM" | sed "s/export//" > ~/.nvm-source; \
		fi \
	else \
		cat ~/.bashrc | grep "export NVM" | sed "s/export//" > ~/.nvm-source; \
	fi

read-source-file: write-source-file
	@if [ ! -f ~/.nvm-source ]; then \
		echo "Source file could not be read"; \
		exit 1; \
	fi

	@for line in $$(cat ~/.nvm-source); do \
		export $$line; \
	done; \
	echo '. "$$NVM_DIR/nvm.sh"' >> ~/.nvm-source;

	@if [[ "$(NVM_DIR)" == "" || ! -f "$(NVM_DIR)/nvm.sh" ]]; then \
		mkdir -p $(HOME)/.nvm; \
		export NVM_DIR=$(HOME)/.nvm; \
		curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v$(NVM_VERSION)/install.sh | bash; \
		echo ""; \
		$(MAKE) write-source-file; \
		for line in $$(cat ~/.nvm-source); do \
			export $$line; \
		done; \
		echo '. "$$NVM_DIR/nvm.sh"' >> ~/.nvm-source; \
	fi

	@current_nvm_version=$$(. ~/.nvm-source && nvm --version); \
	echo "NVM Versions (current/expected): $$current_nvm_version/$(NVM_VERSION)";

upgrade-node:
	@TEMPDIR=/tmp/node-upgrade; \
	if [[ -d $(NVM_DIR)/versions ]]; then \
		rm -rf $$TEMPDIR; \
		mkdir $$TEMPDIR; \
		cp -rf $(NVM_DIR)/versions $$TEMPDIR; \
		echo "Node versions temporarily backed up to: $$TEMPDIR"; \
	fi; \
	rm -rf $(NVM_DIR); \
	$(MAKE) read-source-file; \
	if [[ -d $$TEMPDIR/versions ]]; then \
		cp -rf $$TEMPDIR/versions $(NVM_DIR); \
		echo "Restored node versions from: $$TEMPDIR"; \
	fi;

.PHONY: install-nvm
install-nvm:
	@echo ""
	@echo "[Install Node Version Manager]"
	@echo ""

	@if [[ "$(NVM_VERSION)" == "" ]]; then \
		echo "NVM_VERSION cannot be empty."; \
		exit 1; \
	fi

	@$(MAKE) read-source-file

	@current_nvm_version=$$(. ~/.nvm-source && nvm --version); \
	if [[ "$(NVM_VERSION)" != "$$current_nvm_version" ]]; then \
		$(MAKE) upgrade-node; \
	fi

.PHONY: install-node
install-node: install-nvm
	@echo ""
	@echo "[Install Node]"
	@echo ""

	@. ~/.nvm-source && nvm install $(NODE_VERSION) \
		&& nvm use $(NODE_VERSION) \
		&& nvm alias default $(NODE_VERSION);

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: bootstrap
bootstrap: install-node ## Build project
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
