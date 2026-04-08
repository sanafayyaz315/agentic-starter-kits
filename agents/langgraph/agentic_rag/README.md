<div style="text-align: center;">

![LangGraph Logo](/images/langgraph_logo.svg)

# RAG Agent

</div>

---

## What this agent does

RAG agent that indexes documents in a vector store (Milvus) and retrieves relevant chunks to augment the LLM's answers
with your own data.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Podman](https://podman.io/) or [Docker](https://www.docker.com/) — for local container builds (Option A)
- [oc](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html) — for
  OpenShift deployment
- [GNU Make](https://www.gnu.org/software/make/) and a bash-compatible shell — on Windows,
  use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) (recommended)
  or [Git Bash](https://git-scm.com/downloads)

## Local Development

#### Initiating base

Here you copy .env.example file into .env

```bash
cd agents/langgraph/agentic_rag
make init
```

Edit `.env` with your configuration, then:

See [Local Development](../../../docs/local-development.md) for Ollama + Llama Stack setup for local model serving.

#### Pointing to a remotely hosted model

```ini
API_KEY=your-api-key-here
BASE_URL=https://your-model-endpoint.com/v1
MODEL_ID=llama-3.1-8b-instruct
EMBEDDING_MODEL=your-embedding-model
VECTOR_STORE_PATH=/data/milvus_lite.db
```

**Notes:**

- `API_KEY` — your API key or contact your cluster administrator
- `BASE_URL` — should end with `/v1`
- `MODEL_ID` — model identifier available on your endpoint

#### Creating environment

Now you will remove old .venv and create new. Next dependencies will be installed.

```bash
make env
```

#### Setup Ollama

This will install ollama if it is not installed already. Then pull needed models for local work.
The default model is `llama3.2:3b`. To use a different model, pass `MODEL=`:
`make ollama MODEL=llama3.1:8b`

This also pulls the embedding model (`embeddinggemma:latest`) required for RAG.

```bash
make ollama
```

#### Run llama server

> **Keep this terminal open** – the server needs to keep running.
> You should see output indicating the server started on `http://localhost:8321`.

```bash
make llama-server
```

#### Load documents into vector store

**Important:** Before running the agent, you must load documents into the vector store. If you already have a
`VECTOR_STORE_ID`, paste it into your `.env`. Otherwise, create one by running the document loader:

```bash
make load-docs
```

This will:

- Read documents from the file specified in `DOCS_TO_LOAD`
- Split documents into chunks (512 characters with 128 overlap by default)
- Generate embeddings using the model specified in `EMBEDDING_MODEL`
- Store chunks in the Milvus Lite vector database at `VECTOR_STORE_PATH`

#### Run the interactive web application

> **Keep this terminal open** – the app needs to keep running.
> You should see output indicating the app started on `http://localhost:8000`.

```bash
cd agents/langgraph/agentic_rag
make run-app           # fails if port is already in use and print steps TO-DO
```

#### Interactive CLI

For terminal-based testing without a browser:

```bash
cd agents/langgraph/agentic_rag
make run-cli
```

#### Standalone Flask Playground (alternative)

You can also run the playground as a separate Flask app that proxies to the agent:

```bash
# Terminal 1: Start the agent
make run-app

# Terminal 2: Open in the same directory as Terminal 1
uv run flask --app playground/app run --port 5050
```

| Variable    | Default                 | Description                  |
|-------------|-------------------------|------------------------------|
| `AGENT_URL` | `http://localhost:8000` | URL of the running agent API |

If the agent runs on a different host or port:

```bash
AGENT_URL=https://your-agent-url uv run flask --app playground/app run --port 5050
```

#### Tracing with a local MLflow server

To enable MLflow tracing, add the following to your `.env`:

```ini
MLFLOW_TRACKING_URI="http://localhost:5000"
MLFLOW_EXPERIMENT_NAME="Langgraph RAG Local Experiment"
MLFLOW_HTTP_REQUEST_TIMEOUT=2
MLFLOW_HTTP_REQUEST_MAX_RETRIES=0
```

Then start the MLflow server in a separate terminal:

```bash
# Start the MLflow server
uv run --extra tracing mlflow server --port 5000
```

When `MLFLOW_TRACKING_URI` is set, `make run-app` and `make run-cli` will automatically install the tracing dependency.

#### Tracing with an OpenShift MLflow server

To enable tracing and logging with MLflow on your OpenShift cluster, add the following environment variables to your
`.env` file:

```ini
MLFLOW_TRACKING_URI="https://<openshift-dashboard-url>/mlflow"
MLFLOW_TRACKING_TOKEN="<your-openshift-token>"
MLFLOW_EXPERIMENT_NAME="<your-experiment-name>"
MLFLOW_TRACKING_INSECURE_TLS="true"
MLFLOW_WORKSPACE="<your project name>"
```

**Notes:**

- `MLFLOW_TRACKING_URI` - Replace `<openshift-dashboard-url>` with your OpenShift cluster's data science gateway URL
- `MLFLOW_TRACKING_TOKEN` - Your openshift authentication token. It can be obtained from the openshift console.
- `MLFLOW_EXPERIMENT_NAME` - A descriptive name for your experiment (e.g., "Langgraph RAG Cluster Demo")
- `MLFLOW_TRACKING_INSECURE_TLS` - Set to `"true"` if your OpenShift cluster does not use trusted certificates
- `MLFLOW_WORKSPACE` - Project name

- Tracing is optional; if you do not set `MLFLOW_TRACKING_URI`, the application will run without MLflow logging.

- If `MLFLOW_TRACKING_URI` is set, the application will attempt to connect to the MLflow server at startup. If the
  server is unreachable, the application will log a warning and continue running without tracing.

- You can control how long the application waits for the MLflow server by setting `MLFLOW_HEALTH_CHECK_TIMEOUT` (in
  seconds, default: `5`).

## Deploying to OpenShift

### Setup

```bash
cd agents/langgraph/agentic_rag
make init
```

### Configuration

Edit `.env` with your model endpoint and container image:

```ini
API_KEY=your-api-key-here
BASE_URL=https://your-model-endpoint.com/v1
MODEL_ID=llama-3.1-8b-instruct
CONTAINER_IMAGE=quay.io/your-username/langgraph-agentic-rag:latest
EMBEDDING_MODEL=your-embedding-model
VECTOR_STORE_PATH=/data/milvus_lite.db
```

**Notes:**

- `API_KEY` - your API key or contact your cluster administrator
- `BASE_URL` - should end with `/v1`
- `MODEL_ID` - model identifier available on your endpoint
- `CONTAINER_IMAGE` – full image path where the agent container will be pushed and pulled from. The image is built
  locally, pushed to this registry, and then deployed to OpenShift.

  Format: `<registry>/<namespace>/<image-name>:<tag>`

  Examples:

    - Quay.io: `quay.io/your-username/langgraph-agentic-rag:latest`
    - Docker Hub: `docker.io/your-username/langgraph-agentic-rag:latest`
    - GHCR: `ghcr.io/your-org/langgraph-agentic-rag:latest`

  > **Note:** OpenShift must be able to pull the container image. Make the image **public**, or configure
  an [image pull secret](https://docs.openshift.com/container-platform/latest/openshift_images/managing_images/using-image-pull-secrets.html)
  for private registries.

### Building the Container Image

Login to OC

```bash
oc login -u "login" -p "password" https://super-link-to-cluster:111
```

Login ex. Docker

```bash
docker login -u='login' -p='password' quay.io
```

#### Option A: Build locally and push to a registry

Requires Podman (or Docker) and a registry account (e.g., Quay.io).

```bash
make build    # builds the image locally
make push     # pushes to the registry specified in CONTAINER_IMAGE
```

#### Option B: Build and deploy using deploy.sh

This script builds the image, pushes it, creates secrets, and deploys to OpenShift in one step:

```bash
make deploy
```

This will:

- Build and push the Docker image
- Create Kubernetes secret for API key
- Deploy the agent to OpenShift
- Create Service and Route

### Verify deployment

After deploying, the application may take about a minute to become available while the pod starts up.

```bash
oc get route langgraph-agentic-rag -o jsonpath='{.spec.host}'
```

### Remove deployment (`make undeploy`)

```bash
make undeploy
```

## Tests

```bash
make test
```

## API Endpoints

### POST /chat/completions

Non-streaming:

```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is LangChain?"}], "stream": false}'
```

Streaming:

```bash
curl -sN -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is LangChain?"}], "stream": true}'
```

Pretty Printed Stream:

```bash
curl -sN -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is LangChain?"}], "stream": true}' |
   jq -R -r -j --stream 'scan("^data:(.*)")[] | fromjson.choices[0].delta.content // empty'
```

### GET /health

```bash
curl http://localhost:8000/health
```

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Llama Stack Documentation](https://llama-stack.readthedocs.io/)
- [Ollama Documentation](https://ollama.com/docs)
- [Milvus Documentation](https://milvus.io/docs)
