# second-brain dev commands
#
# Container (devcontainer):  make dev
# Host (macOS):              make dev && make restart
#
# Environment detection: /workspace + UV_PROJECT_ENVIRONMENT → container, otherwise → host

.PHONY: dev restart test build-frontend install help

REPO := $(shell pwd)

# Detect environment
ifdef UV_PROJECT_ENVIRONMENT
  IN_CONTAINER := 1
endif
ifneq ($(wildcard /workspace),)
  IN_CONTAINER := 1
endif

help:
	@echo "Usage:"
	@echo "  make dev       — build frontend + reinstall Python package (container or host)"
	@echo "  make restart   — restart launchd services (HOST only)"
	@echo "  make test      — run full test suite"
	@echo "  make build-frontend — build frontend bundle only"
	@echo "  make install   — reinstall uv tool only"

build-frontend:
	npm run build --prefix "$(REPO)/frontend"

install:
	uv tool install --python 3.13 --editable --force "$(REPO)"

dev: build-frontend install
ifdef IN_CONTAINER
	@echo ""
	@echo "  [CONTAINER] Build complete. Run 'make restart' on HOST to pick up changes."
else
	$(MAKE) restart
endif

restart:
ifdef IN_CONTAINER
	@echo "  [ERROR] 'make restart' must be run on the HOST — launchd is not available in the container."
	@exit 1
else
	@echo "Restarting launchd services..."
	-launchctl stop com.secondbrain.api   2>/dev/null
	-launchctl stop com.secondbrain.watch 2>/dev/null
	uv tool install --python 3.13 --editable --force "$(REPO)"
	-launchctl start com.secondbrain.api   2>/dev/null
	-launchctl start com.secondbrain.watch 2>/dev/null
	@echo "Done. GUI at http://localhost:37491/ui"
endif

test:
	uv run pytest tests/ -q --tb=short
