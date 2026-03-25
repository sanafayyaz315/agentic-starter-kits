<div style="text-align: center;">

![LlamaIndex Logo](/images/llamaindex_logo.svg)

# WebSearch Agent

</div>

---

## What this agent does

Agent built on LlamaIndex that uses a web search tool to query the internet and use the results in its answers.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Podman](https://podman.io/) or [Docker](https://www.docker.com/) — for local container builds (Option A)
- [oc](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html) — for OpenShift deployment
- [Helm](https://helm.sh/) — for deploying to Kubernetes/OpenShift
- [GNU Make](https://www.gnu.org/software/make/) and a bash-compatible shell — on Windows, use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) (recommended) or [Git Bash](https://git-scm.com/downloads)

## Quick Start

```bash
cd agents/llamaindex/websearch_agent
make init        # creates .env from .env.example
# Edit .env with your API_KEY, BASE_URL, MODEL_ID
make run         # starts web playground UI on http://localhost:8000
make run-cli     # interactive terminal chat (no web server)
```

## Configuration

### Local

```ini
API_KEY=not-needed
BASE_URL=http://localhost:8321/v1
MODEL_ID=ollama/llama3.2:3b
```

See [Local Development](../../../docs/local-development.md) for Ollama + Llama Stack setup for local model serving.

#### Tracing

```ini
MLFLOW_TRACKING_URI="http://localhost:5000"
MLFLOW_EXPERIMENT_NAME="LlamaIndex Local Experiment"
MLFLOW_HTTP_REQUEST_TIMEOUT=2
MLFLOW_HTTP_REQUEST_MAX_RETRIES=0
```

### OpenShift / Remote API

```ini
API_KEY=your-api-key-here
BASE_URL=https://your-model-endpoint.com/v1
MODEL_ID=llama-3.1-8b-instruct
CONTAINER_IMAGE=quay.io/your-username/llamaindex-websearch-agent:latest
```

**Notes:**

- `API_KEY` - your API key or contact your cluster administrator
- `BASE_URL` - should end with `/v1`
- `MODEL_ID` - model identifier available on your endpoint
- `CONTAINER_IMAGE` – full image path where the agent container will be pushed and pulled from. The image is built
  locally, pushed to this registry, and then deployed to OpenShift.

  Format: `<registry>/<namespace>/<image-name>:<tag>`

  Examples:

    - Quay.io: `quay.io/your-username/llamaindex-websearch-agent:latest`
    - Docker Hub: `docker.io/your-username/llamaindex-websearch-agent:latest`
    - GHCR: `ghcr.io/your-org/llamaindex-websearch-agent:latest`

#### Tracing

To enable tracing and logging with MLflow on your OpenShift cluster, add the following environment variables to your `.env` file:

```ini
MLFLOW_TRACKING_URI="https://<openshift-dashboard-url>/mlflow"
MLFLOW_TRACKING_TOKEN="<your-openshift-token>"
MLFLOW_EXPERIMENT_NAME="<your-experiment-name>"
MLFLOW_TRACKING_INSECURE_TLS="true"
MLFLOW_WORKSPACE="default"
```

**Notes:**
- `MLFLOW_TRACKING_URI` - Replace `<openshift-dashboard-url>` with your OpenShift cluster's data science gateway URL
- `MLFLOW_TRACKING_TOKEN` - Your openshift authentication token. It can be obtained from the openshift console.
- `MLFLOW_EXPERIMENT_NAME` - A descriptive name for your experiment (e.g., "LlamaIndex Cluster Demo")
- `MLFLOW_TRACKING_INSECURE_TLS` - Set to `"true"` if your OpenShift cluster does not use trusted certificates
- `MLFLOW_WORKSPACE` - Project name

- Tracing is optional; if you do not set `MLFLOW_TRACKING_URI`, the application will run without MLflow logging.

- If `MLFLOW_TRACKING_URI` is set, the application will attempt to connect to the MLflow server at startup. If the server is unreachable, the application will log a warning and continue running without tracing.

- You can control how long the application waits for the MLflow server by setting `MLFLOW_HEALTH_CHECK_TIMEOUT` (in seconds, default: `5`).

## Deploying to OpenShift

```bash
# Option A: Build locally with Podman (or Docker) and push to a registry
make build            # builds container image locally
make push             # pushes image to registry
make dry-run          # (optional) preview rendered Helm manifests
make deploy           # deploys via Helm

# Option B: Build in-cluster on OpenShift (no Podman/Docker needed)
make build-openshift  # builds image via OpenShift BuildConfig
# Set CONTAINER_IMAGE in .env to the internal registry path printed after the build
make dry-run          # (optional) preview rendered Helm manifests
make deploy

# Remove deployment from cluster
make undeploy
```

See [OpenShift Deployment](../../../docs/openshift-deployment.md) for details.

### Testing on OpenShift

After deploying, the application may take about a minute to become available while the pod starts up.

The route URL is printed after `make deploy`. You can also retrieve it manually:

```bash
oc get route llamaindex-websearch-agent -o jsonpath='{.spec.host}'
```

Replace `http://localhost:8000` with `https://<YOUR_ROUTE_URL>` in the API examples below.

## API Endpoints

### POST /chat/completions

Non-streaming:

```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Which company is considered the best?"}], "stream": false}'
```

Streaming:

```bash
curl -sN -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Which company is considered the best?"}], "stream": true}'
```

Pretty Printed Stream:

```bash
curl -sN -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Which company is considered the best?"}], "stream": true}' |
   jq -R -r -j --stream 'scan("^data:(.*)")[] | fromjson.choices[0].delta.content // empty'
```

### GET /health

```bash
curl http://localhost:8000/health
```

## Playground UI

A browser-based chat interface is served directly by the agent at the root URL — no separate process needed.

```bash
make run
```

Open [http://localhost:8000](http://localhost:8000) in your browser. A green dot in the header means the agent is connected and ready.

When deployed to OpenShift, the playground is available at the route URL printed by `make deploy`.

### Interactive CLI Chat

For terminal-based testing without a browser:

```bash
make run-cli
```

This launches an interactive prompt where you can pick predefined questions or type your own. Tool calls and results are displayed inline with colored output.

### Standalone Flask Playground (alternative)

You can also run the playground as a separate Flask app that proxies to the agent:

```bash
# Terminal 1: Start the agent
make run

# Terminal 2: Open in the same directory as Terminal 1
uv pip install flask
uv run flask --app playground.app run --port 5050
```

| Variable    | Default                  | Description                     |
|-------------|--------------------------|---------------------------------|
| `AGENT_URL` | `http://localhost:8000`  | URL of the running agent API    |

If the agent runs on a different host or port:

```bash
AGENT_URL=https://your-agent-url uv run flask --app playground.app run --port 5050
```

## Tests

```bash
make test
```

## Resources

- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [LlamaIndex Workflows](https://docs.llamaindex.ai/en/stable/module_guides/workflow/)
- [Llama Stack Documentation](https://llama-stack.readthedocs.io/)
