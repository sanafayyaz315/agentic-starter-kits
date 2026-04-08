SHELL          := bash
AGENT_NAME     := langgraph-agentic-rag
CONTAINER_CLI  := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
MODEL          ?= llama3.2:3b

.PHONY: init re-init env ollama llama-server run-app run-app-fresh run-cli load-docs build push deploy undeploy test help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

re-init: ## Activate venv and reload .env variables
	@source .venv/bin/activate && set -a && source .env && set +a && \
	  echo "Venv activated and .env variables loaded."

init: ## Copy .env.example to .env for configuration
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example — edit it with your configuration"; else echo ".env already exists — skipping"; fi

env: ## Create venv, load .env, and install dependencies
	@echo "==> Creating virtual environment and installing dependencies..." && \
	  rm -rf .venv && \
	  uv sync --python 3.12 && \
	  echo "==> Load .env variables..." && \
	  source .venv/bin/activate && set -a && source .env && set +a && \
	  echo "" && \
	  echo "Done. Next steps:" && \
	  echo "  make ollama        # install Ollama and pull models" && \
	  echo "  make llama-server  # start Llama Stack server"

ollama: ## Install Ollama, start it, and pull models
	@source .venv/bin/activate && set -a && source .env && set +a && \
	if command -v ollama >/dev/null 2>&1; then \
	  echo "==> Ollama already installed, skipping..."; \
	else \
	  echo "==> Installing Ollama..." && \
	  curl -fsSL https://ollama.com/install.sh | sh; \
	fi && \
	  echo "==> Starting Ollama service..." && \
	  ollama serve &>/dev/null & \
	  echo "Waiting for Ollama to be ready..." && \
	  until ollama list >/dev/null 2>&1; do sleep 1; done && \
	  echo "==> Pulling $(MODEL)..." && \
	  ollama pull $(MODEL) && \
	  echo "==> Pulling embedding model (embeddinggemma:latest)..." && \
	  ollama pull embeddinggemma:latest && \
	  echo "==> Creating Milvus dir..." && \
	  mkdir -p ../../../milvus_data && \
	  echo "" && \
	  echo "Done. Run 'make llama-server' to start the Llama Stack server."

llama-server: ## Install llama-stack and start Llama Stack server
	@source .venv/bin/activate && set -a && source .env && set +a && \
	  echo "==> Installing llama-stack..." && \
	  uv pip install "llama-stack==0.5.0" "llama-stack-api==0.5.0" ollama && \
	  echo "==> Killing any existing process on port 8321..." && \
	  lsof -ti:8321 | xargs kill -9 2>/dev/null; true && \
	  echo "==> Starting Llama Stack server on port 8321..." && \
	  llama stack run ../../../run_llama_server.yaml

run-app: ## Run agent locally with hot-reload
	@source .venv/bin/activate && set -a && source .env && set +a && \
	  if lsof -ti:$${PORT:-8000} >/dev/null 2>&1; then \
	    echo "ERROR: Port $${PORT:-8000} is already in use." && \
	    echo "  Change PORT in .env or run: make run-app-fresh" && \
	    exit 1; \
	  fi && \
	  uv run $${MLFLOW_TRACKING_URI:+--extra tracing} uvicorn main:app --host 0.0.0.0 --port $${PORT:-8000} --reload --reload-exclude .venv

run-app-fresh: ## Kill existing process on port and run agent with hot-reload
	@source .venv/bin/activate && set -a && source .env && set +a && \
	  echo "==> Killing existing process on port $${PORT:-8000}..." && \
	  lsof -ti:$${PORT:-8000} | xargs kill -9 2>/dev/null; true && \
	  uv run $${MLFLOW_TRACKING_URI:+--extra tracing} uvicorn main:app --host 0.0.0.0 --port $${PORT:-8000} --reload --reload-exclude .venv

run-cli: ## Run interactive CLI chat (no web server)
	@source .venv/bin/activate && set -a && source .env && set +a && \
	  cd examples && uv run $${MLFLOW_TRACKING_URI:+--extra tracing} python execute_ai_service_locally.py

load-docs: ## Load documents into vector store
	@source .venv/bin/activate && set -a && source .env && set +a && \
	  uv run python data/load_documents.py

build: ## Build container image locally (podman/docker)
	@[ -n "$(CONTAINER_CLI)" ] || { echo "ERROR: neither podman nor docker found in PATH"; exit 1; } && \
	  source .env && \
	  [ -n "$${CONTAINER_IMAGE}" ] || { echo "ERROR: CONTAINER_IMAGE is not set in .env"; exit 1; } && \
	  cp -r ../../../images ./images && trap 'rm -rf ./images' EXIT && \
	  $(CONTAINER_CLI) build --platform linux/amd64 -t "$${CONTAINER_IMAGE}" -f Dockerfile .

push: ## Push container image to registry
	@[ -n "$(CONTAINER_CLI)" ] || { echo "ERROR: neither podman nor docker found in PATH"; exit 1; } && \
	  source .env && \
	  [ -n "$${CONTAINER_IMAGE}" ] || { echo "ERROR: CONTAINER_IMAGE is not set in .env"; exit 1; } && \
	  $(CONTAINER_CLI) push "$${CONTAINER_IMAGE}"

deploy: ## Deploy to OpenShift using deploy.sh
	@chmod +x deploy.sh && ./deploy.sh

undeploy: ## Remove deployment from OpenShift
	@oc delete deployment,service,route -l app=$(AGENT_NAME) --ignore-not-found && \
	  oc delete secret $(AGENT_NAME)-secrets --ignore-not-found && \
	  echo "Deployment removed."

test: ## Run tests
	uv run --extra dev python -m pytest tests/