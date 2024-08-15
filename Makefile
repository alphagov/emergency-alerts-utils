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
	@for line in $$(cat ~/.nvm-source); do \
		export $$line; \
	done

	@echo '. "$$NVM_DIR/nvm.sh"' >> ~/.nvm-source;

	@current_nvm_version=$$(. ~/.nvm-source && nvm --version); \
	echo "NVM Versions (current/expected): $$current_nvm_version/$(NVM_VERSION)"; \
	echo "";

.PHONY: install-nvm
install-nvm:
	@echo ""
	@echo "[Install Node Version Manager]"
	@echo ""

	@if [ ! -f ~/.nvm-source ]; then \
		rm -rf $(NVM_DIR); \
		curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v$(NVM_VERSION)/install.sh | bash; \
		echo ""; \
	fi

	@$(MAKE) read-source-file

	@current_nvm_version=$$(. ~/.nvm-source && nvm --version); \
	if [[ "$(NVM_VERSION)" == "$$current_nvm_version" ]]; then \
		echo "No need up adjust NVM versions."; \
	else \
		rm -rf $(NVM_DIR); \
		curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v$(NVM_VERSION)/install.sh | bash; \
		echo ""; \
	fi

	@$(MAKE) read-source-file

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
