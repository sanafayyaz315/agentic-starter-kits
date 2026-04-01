<div style="text-align: center;">

# A2A: LangGraph ↔ CrewAI

</div>

---

## What this agent does

An **A2A (Agent-to-Agent)** example: a **CrewAI** pod exposes an A2A JSON-RPC server, and a **LangGraph** pod acts as an orchestrator that calls the Crew specialist over HTTP/A2A inside the cluster (or locally). One container image is built from a single `Dockerfile`; **`A2A_ROLE`** in the pod (`crew` vs `langgraph`) selects which process runs.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Docker](https://www.docker.com/) — for local container builds and push (the `Makefile` uses `docker` or `podman` if present in `PATH`)
- [oc](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html) — for OpenShift deployment
- [Helm](https://helm.sh/) — for deploying to Kubernetes/OpenShift
- [GNU Make](https://www.gnu.org/software/make/) and a bash-compatible shell — on Windows, use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) (recommended) or [Git Bash](https://git-scm.com/downloads)

---

## Deploying Locally

### Setup

```bash
cd agents/a2a/langgraph_crewai_agent
make init        # creates .env from template.env if missing
```

Create and activate a virtual environment (Python 3.12+) in this directory using [uv](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.12
source .venv/bin/activate
```

(On Windows: `.venv\Scripts\activate`)

### Configuration

#### Pointing to a locally hosted model

You can use placeholders for container images if you only run Python locally:

```
API_KEY=your-key-or-not-needed
BASE_URL=http://localhost:8321/v1
MODEL_ID=ollama/llama3.1:8b
CONTAINER_IMAGE=not-needed
CREW_A2A_PUBLIC_URL=http://127.0.0.1:9100
LANGGRAPH_A2A_PUBLIC_URL=http://127.0.0.1:9200
CREW_A2A_URL=http://127.0.0.1:9100
CREW_A2A_PORT=9100
LANGGRAPH_A2A_PORT=9200
```

See [Local Development](../../../docs/local-development.md) for Ollama + Llama Stack setup for local model serving.

#### OpenShift Cluster (values for later `make build` / `make deploy`)

Edit `.env` and fill in all required values:

```
API_KEY=your-api-key-here
BASE_URL=https://your-llama-stack.example.com/v1
MODEL_ID=your-model-id
CONTAINER_IMAGE=quay.io/your-org/a2a-langgraph-crewai:latest
```

For deploy, **`make deploy`** sets `CREW_A2A_PUBLIC_URL` / `LANGGRAPH_A2A_PUBLIC_URL` from OpenShift Routes (Helm phase 2). Local defaults in `template.env` are for running servers on your machine.

**Notes:**

- `API_KEY` — your API key or contact your cluster administrator or LLM provider
- `BASE_URL` — must include `/v1` for OpenAI-compatible chat
- `MODEL_ID` — model id accepted by that endpoint
- `CONTAINER_IMAGE` — see [Deploying to OpenShift — Configuration](#configuration-1) for registry format, examples, and pull secrets. By default `make build` strips the tag and pushes **the same image** to two refs (**`:crew`** and **`:langgraph`**) so each Deployment keeps a distinct pull URL; roles differ via **`A2A_ROLE`**. Optionally set `CONTAINER_IMAGE_CREW` and `CONTAINER_IMAGE_LANGGRAPH` instead (e.g. two separate repos).

### Running the agent

```bash
uv sync
```

Export variables from `.env`, then start both servers (two terminals):

```bash
set -a && source .env && set +a
```

```bash
# Terminal 1
uv run python -m a2a_langgraph_crewai.crew_a2a_server

# Terminal 2
uv run python -m a2a_langgraph_crewai.langgraph_a2a_server
```

Default ports: **9100** (Crew), **9200** (LangGraph). Do not set `PORT` unless you mirror the container (`8080`).

#### Playground (LangGraph orchestrator)

With the LangGraph server running (terminal 2), open **http://127.0.0.1:9200/** in a browser. The chat uses **A2A JSON-RPC** on **`POST /`** with **`message/send`** (request body = `SendMessageRequest`, same shape as the **curl** examples under **Deploying to OpenShift**). The right-hand panel shows the outgoing JSON and the raw JSON-RPC response. The server also exposes **`POST /chat/completions`** (OpenAI-style) for parity with other agents. For local `curl`, use `http://127.0.0.1:9200` instead of the OpenShift route host.

---

## Deploying to OpenShift

Uses the same pattern as other agents in this repo: **[Helm](https://helm.sh/)** + **`Makefile`**. The manifest source is **`charts/a2a-langgraph-crewai/`** (two Deployments, two Services, two Routes, one Secret).

### Setup

```bash
cd agents/a2a/langgraph_crewai_agent
make init        # creates .env from template.env if missing
```

Log in to the cluster and registry:

```bash
oc login --token=<token> --server=https://<cluster-api-url>
oc project <namespace>
docker login -u='login' -p='password' quay.io
```

### Configuration

Edit `.env` with your model endpoint and container image(s):

```
API_KEY=your-api-key-here
BASE_URL=https://your-model-endpoint.com/v1
MODEL_ID=your-model-id
CONTAINER_IMAGE=quay.io/your-username/a2a-langgraph-crewai:latest
```

**Notes:**

- `API_KEY` — your API key or contact your cluster administrator
- `BASE_URL` — should end with `/v1`
- `MODEL_ID` — model identifier available on your endpoint
- `CONTAINER_IMAGE` — full image path where the container will be pushed and pulled from. **`make build`** builds once and pushes **two** tags (`:crew` and `:langgraph`) from the same `CONTAINER_IMAGE` stem so each Deployment references a distinct image ref. Alternatively set **`CONTAINER_IMAGE_CREW`** and **`CONTAINER_IMAGE_LANGGRAPH`** to two full refs if you prefer separate repositories or tags.

  Format: `<registry>/<namespace>/<image-name>:<tag>`

  Examples:

  - Quay.io: `quay.io/your-username/a2a-langgraph-crewai:latest`
  - Docker Hub: `docker.io/your-username/a2a-langgraph-crewai:latest`
  - GHCR: `ghcr.io/your-org/a2a-langgraph-crewai:latest`

  > **Note:** OpenShift must be able to pull the container images. Make the images **public**, or configure an [image pull secret](https://docs.openshift.com/container-platform/latest/openshift_images/managing_images/using-image-pull-secrets.html) for private registries (repeat for both image refs if they differ).

### Building the container image

#### Build and push to a registry

Requires Docker (or Podman on `PATH`) and a registry account (e.g., Quay.io).

```bash
make build    # buildx push :crew and :langgraph
```

### Deploying

#### Preview manifests (`make dry-run`)

```bash
make dry-run          # preview rendered Helm manifests (secrets redacted)
```

#### Deploy (`make deploy`)

```bash
make deploy
```

**What `make deploy` does**

1. **Helm phase 1** — `deploymentsEnabled=false`: Secret, Services, Routes (so OpenShift assigns hostnames).
2. Waits until **`oc get route`** returns hosts for `a2a-crew-agent` and `a2a-langgraph-agent`.
3. **Helm phase 2** — `deploymentsEnabled=true` with `crewPublicUrl` / `langgraphPublicUrl` set to `https://…` from those hosts.
4. Waits for rollouts.

The LangGraph pod uses in-cluster **`CREW_A2A_URL=http://a2a-crew-agent:8080`**.

#### Verify deployment

After deploying, the application may take about a minute to become available while the pods start.

Route hosts are printed after `make deploy`. Retrieve them manually:

```bash
oc get route a2a-crew-agent a2a-langgraph-agent -o wide
# LangGraph (public API / playground):
oc get route a2a-langgraph-agent -o jsonpath='{.spec.host}'
```

#### Remove deployment (`make undeploy`)

```bash
make undeploy
```

See [OpenShift Deployment](../../../docs/openshift-deployment.md) for more details.

### API examples (LangGraph route)

Use the **LangGraph** Route (`a2a-langgraph-agent`), not the Crew route. Routes terminate TLS at the edge; use **`https://`**.

Get the route hostname (replace **`<YOUR_ROUTE_URL>`** below with that host, e.g. `a2a-langgraph-agent-myproject.apps.example.com`):

```bash
oc get route a2a-langgraph-agent -o jsonpath='{.spec.host}'
```

**Agent card**

```bash
curl -sS "https://<YOUR_ROUTE_URL>/.well-known/agent-card.json"
```

**A2A JSON-RPC (`message/send` on `POST /`)**

Same protocol as the browser playground: JSON-RPC 2.0 body = `SendMessageRequest` (see [a2a-sdk](https://pypi.org/project/a2a-sdk/)). Use a unique `messageId` (e.g. 32 hex chars) per request. The example below uses a **single-line** `-d '…'` body (no `'` inside the user text, so bash quoting stays simple):

```bash
curl -sS -X POST "https://<YOUR_ROUTE_URL>/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Use the web search tool to find the Red Hat encrypted string."}],"messageId":"0123456789abcdef0123456789abcdef"}},"id":"curl-req-1"}'
```

The response is JSON-RPC (`result` or `error`), not OpenAI chat format.

**OpenAI-style chat (`POST /chat/completions`)**

Also available for parity with other agents in this repo (non-streaming example):

```bash
curl -sS -X POST "https://<YOUR_ROUTE_URL>/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Use the web search tool to find the Red Hat encrypted string."}],"stream":false}'
```

### Operational notes
- **A2A LangGraph → Crew**: `a2a_reply.send_a2a_text_message` logs each real 
`message/send` at **INFO** (peer URL, JSON-RPC id, text length, short preview). 
For full request/response JSON as seen by the client, run the LangGraph pod with 
**`LOG_LEVEL=DEBUG`** (or set the logger `a2a_langgraph_crewai.a2a_reply` to 
DEBUG) and read **`oc logs`** for the orchestrator Deployment.

## Resources

- [A2A Python SDK](https://pypi.org/project/a2a-sdk/)
- [Deploying to OpenShift (generic)](../../../docs/openshift-deployment.md)
- [Local Development](../../../docs/local-development.md)
- Related patterns: `agents/llamaindex/websearch_agent/` (Helm + Makefile), `agents/crewai/websearch_agent/`, `agents/langgraph/react_agent/`
