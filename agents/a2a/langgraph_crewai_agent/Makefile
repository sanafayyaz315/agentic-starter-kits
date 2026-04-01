SHELL          := bash
AGENT_NAME     := $(shell python3 -c "import re; print(re.search(r'^name:\s*(.+)', open('agent.yaml').read(), re.M).group(1).strip())")
CHART_DIR      := ../../../charts/a2a-langgraph-crewai
VALUES_FILE    := values.yaml
CONTAINER_CLI  := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

.PHONY: init build push deploy undeploy dry-run help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

init: ## Create .env from template.env if missing
	@if [ ! -f .env ]; then cp template.env .env && echo "Created .env from template.env — edit it with your configuration"; else echo ".env already exists — skipping"; fi

_check-env:
	@set -a && source .env 2>/dev/null && set +a; \
	  missing=""; \
	  for var in $$(sed -n '/^ *required:/,/^ *[a-z]/{ /^ *- /s/^ *- *//p; }' agent.yaml); do \
	    eval val="\$$$$var"; \
	    [ -n "$$val" ] || missing="$$missing $$var"; \
	  done; \
	  [ -z "$$missing" ] || { echo "ERROR: Missing required env vars:$$missing"; exit 1; }

build: _check-env ## Build and push both images (same Dockerfile, :crew and :langgraph tags)
	@[ -n "$(CONTAINER_CLI)" ] || { echo "ERROR: neither podman nor docker found in PATH"; exit 1; }
	@set -a && source .env && set +a && \
	if [ -n "$${CONTAINER_IMAGE_CREW:-}" ] && [ -n "$${CONTAINER_IMAGE_LANGGRAPH:-}" ]; then \
	  $(CONTAINER_CLI) buildx build --platform linux/amd64 -t "$${CONTAINER_IMAGE_CREW}" -f Dockerfile --push . && \
	  $(CONTAINER_CLI) buildx build --platform linux/amd64 -t "$${CONTAINER_IMAGE_LANGGRAPH}" -f Dockerfile --push . && \
	  echo "Build+push completed for both image refs."; \
	elif [ -n "$${CONTAINER_IMAGE:-}" ]; then \
	  _base="$${CONTAINER_IMAGE%%@*}"; _tail="$${_base##*/}"; \
	  if [[ "$$_tail" == *:* ]]; then _img="$${_base%:*}"; else _img="$$_base"; fi; \
	  CREW="$${_img}:crew"; LG="$${_img}:langgraph"; \
	  echo "Using $$CREW and $$LG"; \
	  $(CONTAINER_CLI) buildx build --platform linux/amd64 -t "$$CREW" -f Dockerfile --push . && \
	  $(CONTAINER_CLI) buildx build --platform linux/amd64 -t "$$LG" -f Dockerfile --push . && \
	  echo "Build+push completed for both image refs."; \
	else \
	  echo "ERROR: Set CONTAINER_IMAGE or both CONTAINER_IMAGE_CREW and CONTAINER_IMAGE_LANGGRAPH in .env"; exit 1; \
	fi

deploy: _check-env ## Two-phase Helm deploy (Routes first, then Deployments with public Agent Card URLs)
	@[ -n "$(CONTAINER_CLI)" ] || true
	@set -a && source .env && set +a && \
	if [ -n "$${CONTAINER_IMAGE_CREW:-}" ] && [ -n "$${CONTAINER_IMAGE_LANGGRAPH:-}" ]; then \
	  CREW_REPO="$${CONTAINER_IMAGE_CREW%:*}"; CREW_TAG="$${CONTAINER_IMAGE_CREW##*:}"; \
	  LG_REPO="$${CONTAINER_IMAGE_LANGGRAPH%:*}"; LG_TAG="$${CONTAINER_IMAGE_LANGGRAPH##*:}"; \
	elif [ -n "$${CONTAINER_IMAGE:-}" ]; then \
	  _base="$${CONTAINER_IMAGE%%@*}"; _tail="$${_base##*/}"; \
	  if [[ "$$_tail" == *:* ]]; then _img="$${_base%:*}"; else _img="$$_base"; fi; \
	  CREW_REPO="$$_img"; CREW_TAG="crew"; LG_REPO="$$_img"; LG_TAG="langgraph"; \
	else \
	  echo "ERROR: Set CONTAINER_IMAGE or both CONTAINER_IMAGE_CREW and CONTAINER_IMAGE_LANGGRAPH in .env"; exit 1; \
	fi && \
	trap 'rm -f .helm-secrets.yaml' EXIT && \
	umask 077 && \
	printf 'secrets:\n  apiKey: "%s"\n' "$${API_KEY}" > .helm-secrets.yaml && \
	echo "=== Helm phase 1: Service, Route, Secret (no Deployments yet) ===" && \
	helm upgrade --install $(AGENT_NAME) $(CHART_DIR) \
	  -f $(VALUES_FILE) \
	  -f .helm-secrets.yaml \
	  --set deploymentsEnabled=false \
	  --set-string image.crew.repository="$$CREW_REPO" \
	  --set-string image.crew.tag="$$CREW_TAG" \
	  --set-string image.langgraph.repository="$$LG_REPO" \
	  --set-string image.langgraph.tag="$$LG_TAG" \
	  --set-string env.BASE_URL="$$BASE_URL" \
	  --set-string env.MODEL_ID="$$MODEL_ID" && \
	echo "=== Waiting for OpenShift Route hostnames ===" && \
	CREW_HOST=""; LG_HOST=""; \
	for _ in $$(seq 1 60); do \
	  CREW_HOST=$$(oc get route a2a-crew-agent -o jsonpath='{.spec.host}' 2>/dev/null || true); \
	  LG_HOST=$$(oc get route a2a-langgraph-agent -o jsonpath='{.spec.host}' 2>/dev/null || true); \
	  [ -n "$$CREW_HOST" ] && [ -n "$$LG_HOST" ] && break; \
	  sleep 1; \
	done && \
	if [ -z "$$CREW_HOST" ] || [ -z "$$LG_HOST" ]; then \
	  echo "ERROR: Could not read route hostnames. Check: oc get route"; exit 1; \
	fi && \
	echo "CREW_A2A_PUBLIC_URL=https://$$CREW_HOST" && \
	echo "LANGGRAPH_A2A_PUBLIC_URL=https://$$LG_HOST" && \
	echo "=== Helm phase 2: Deployments with Agent Card URLs ===" && \
	helm upgrade $(AGENT_NAME) $(CHART_DIR) \
	  -f $(VALUES_FILE) \
	  --reuse-values \
	  --set deploymentsEnabled=true \
	  --set-string crewPublicUrl="https://$$CREW_HOST" \
	  --set-string langgraphPublicUrl="https://$$LG_HOST" && \
	oc rollout status deployment/a2a-crew-agent --timeout=300s && \
	oc rollout status deployment/a2a-langgraph-agent --timeout=300s && \
	echo "=== Done ===" && oc get route a2a-crew-agent a2a-langgraph-agent

undeploy: ## Remove Helm release (all resources)
	helm uninstall $(AGENT_NAME) --ignore-not-found

dry-run: _check-env ## Render Helm manifests (secrets redacted)
	@set -a && source .env && set +a && \
	if [ -n "$${CONTAINER_IMAGE_CREW:-}" ] && [ -n "$${CONTAINER_IMAGE_LANGGRAPH:-}" ]; then \
	  CREW_REPO="$${CONTAINER_IMAGE_CREW%:*}"; CREW_TAG="$${CONTAINER_IMAGE_CREW##*:}"; \
	  LG_REPO="$${CONTAINER_IMAGE_LANGGRAPH%:*}"; LG_TAG="$${CONTAINER_IMAGE_LANGGRAPH##*:}"; \
	elif [ -n "$${CONTAINER_IMAGE:-}" ]; then \
	  _base="$${CONTAINER_IMAGE%%@*}"; _tail="$${_base##*/}"; \
	  if [[ "$$_tail" == *:* ]]; then _img="$${_base%:*}"; else _img="$$_base"; fi; \
	  CREW_REPO="$$_img"; CREW_TAG="crew"; LG_REPO="$$_img"; LG_TAG="langgraph"; \
	else echo "ERROR: Set CONTAINER_IMAGE or both CONTAINER_IMAGE_CREW and CONTAINER_IMAGE_LANGGRAPH"; exit 1; fi && \
	helm template $(AGENT_NAME) $(CHART_DIR) \
	  -f $(VALUES_FILE) \
	  --set secrets.apiKey=REDACTED \
	  --set deploymentsEnabled=true \
	  --set-string crewPublicUrl="https://crew.example.com" \
	  --set-string langgraphPublicUrl="https://langgraph.example.com" \
	  --set-string image.crew.repository="$$CREW_REPO" \
	  --set-string image.crew.tag="$$CREW_TAG" \
	  --set-string image.langgraph.repository="$$LG_REPO" \
	  --set-string image.langgraph.tag="$$LG_TAG" \
	  --set-string env.BASE_URL="$$BASE_URL" \
	  --set-string env.MODEL_ID="$$MODEL_ID"
