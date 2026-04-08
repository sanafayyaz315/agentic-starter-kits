<div style="text-align: center;">

![LangGraph Logo](/images/langgraph_logo.svg)

# Human-in-the-Loop Agent

</div>

---

## What this agent does

Agent with **Human-in-the-Loop (HITL) approval** that pauses execution before running sensitive tools (e.g.
`create_file`) and waits for human review. Simple questions are answered directly without triggering the approval loop.
Built with LangGraph and LangChain.

**How it works:**

```
User Input → LLM decides tool → Is it sensitive?
                                    ├── No  → Execute tool automatically → Return result
                                    └── Yes → PAUSE (interrupt) → Human approves/rejects
                                                                    ├── Approved → Execute tool → Return result
                                                                    └── Rejected → Return rejection message
```

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Podman](https://podman.io/) or [Docker](https://www.docker.com/) — for local container builds (Option A)
- [oc](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html) — for
  OpenShift deployment
- [Helm](https://helm.sh/) — for deploying to Kubernetes/OpenShift
- [GNU Make](https://www.gnu.org/software/make/) and a bash-compatible shell — on Windows,
  use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) (recommended)
  or [Git Bash](https://git-scm.com/downloads)

## Local Development

#### Initiating base

Here you copy .env.example file into .env

```bash
cd agents/langgraph/human_in_the_loop
make init
```

Edit `.env` with your configuration, then:

#### Creating environment

Now you will remove old .venv and create new. Next dependencies will be installed.

```bash
make env
```

#### Setup Ollama

This will install ollama if it is not installed already. Then pull needed models for local work.
The default model is `llama3.2:3b`. To use a different model, pass `MODEL=`:
`make ollama MODEL=llama3.1:8b`

```bash
make ollama
```

#### Run llama server

> **Keep this terminal open** – the server needs to keep running.
> You should see output indicating the server started on `http://localhost:8321`.

```bash
make llama-server
```

#### Run the interactive web application

> **Keep this terminal open** – the app needs to keep running.
> You should see output indicating the app started on `http://localhost:8000`.

```bash
cd agents/langgraph/human_in_the_loop
make run-app           # fails if port is already in use and print steps TO-DO
```

Open [http://localhost:8000](http://localhost:8000) in your browser. A green dot in the header means the agent is
connected and ready.

When the agent pauses for approval, an **Approve / Reject** banner appears directly in the chat.

#### Interactive CLI

For terminal-based testing without a browser:

```bash
cd agents/langgraph/human_in_the_loop
make run-cli
```

This launches an interactive prompt where you can pick predefined questions or type your own. Tool calls and results are
displayed inline with colored output.

## Deploying to OpenShift

### Setup

```bash
cd agents/langgraph/human_in_the_loop
make init
```

### Configuration

Edit `.env` with your model endpoint and container image:

```ini
API_KEY = your-api-key-here
BASE_URL = https://your-model-endpoint.com/v1
MODEL_ID = llama-3.1-8b-instruct
CONTAINER_IMAGE = quay.io/your-username/langgraph-hitl-agent:latest
```

**Notes:**

- `API_KEY` - your API key or contact your cluster administrator
- `BASE_URL` - should end with `/v1`
- `MODEL_ID` - model identifier available on your endpoint
- `CONTAINER_IMAGE` – full image path where the agent container will be pushed and pulled from. The image is built
  locally, pushed to this registry, and then deployed to OpenShift.

  Format: `<registry>/<namespace>/<image-name>:<tag>`

  Examples:

    - Quay.io: `quay.io/your-username/langgraph-hitl-agent:latest`
    - Docker Hub: `docker.io/your-username/langgraph-hitl-agent:latest`
    - GHCR: `ghcr.io/your-org/langgraph-hitl-agent:latest`

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

#### Option B: Build in-cluster via OpenShift BuildConfig

No Podman, Docker, or registry account needed — just the `oc` CLI.

```bash
make build-openshift
```

After the build completes, set `CONTAINER_IMAGE` in your `.env` to the internal registry URL printed after the build.

### Deploying

#### Preview manifests (`make dry-run`)

```bash
make dry-run          # preview rendered Helm manifests (secrets redacted)
```

#### Deploy (`make deploy`)

```bash
make deploy
```

#### Verify deployment

After deploying, the application may take about a minute to become available while the pod starts up.

The route URL is printed after `make deploy`. You can also retrieve it manually:

```bash
oc get route langgraph-hitl-agent -o jsonpath='{.spec.host}'
```

#### Remove deployment (`make undeploy`)

```bash
make undeploy
```

See [OpenShift Deployment](../../../docs/openshift-deployment.md) for more details.

### Testing on OpenShift

Replace `http://localhost:8000` with `https://<YOUR_ROUTE_URL>` in the examples below.

**Step 1: Ask a general question (no approval needed)**

```bash
curl -X POST https://<YOUR_ROUTE_URL>/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is RedHat OpenShift Cluster"}],
    "stream": false,
    "thread_id": "demo-1"
  }'
```

**Step 2: Ask to write that info into a file (triggers approval)**

```bash
curl -X POST https://<YOUR_ROUTE_URL>/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write that information into a file called demo.md"}],
    "stream": false,
    "thread_id": "demo-1"
  }'
```

The agent will pause and return `finish_reason: "pending_approval"` with the `create_file` tool call details.

**Step 3: Approve the file creation**

```bash
curl -X POST https://<YOUR_ROUTE_URL>/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": ""}],
    "thread_id": "demo-1",
    "approval": "yes"
  }'
```

The agent resumes, executes `create_file`, and returns the final result.

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
  -d '{"messages": [{"role": "user", "content": "What is RedHat OpenShift?"}], "stream": false, "thread_id": "demo-1"}'
```

Streaming:

```bash
curl -sN -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is RedHat OpenShift?"}], "stream": true, "thread_id": "demo-1"}'
```

### GET /health

```bash
curl http://localhost:8000/health
```

## Human-in-the-Loop Features

### How Approval Works

This agent classifies tools into two categories:

| Category      | Tools         | Behavior                                  |
|---------------|---------------|-------------------------------------------|
| **Safe**      | general chat  | Responded to directly, no approval needed |
| **Sensitive** | `create_file` | Paused for human review before execution  |

When the LLM decides to call a sensitive tool, the agent:

1. **Pauses** execution using LangGraph's `interrupt()` mechanism
2. **Returns** the pending tool call details with `finish_reason: "pending_approval"`
3. **Includes** a `thread_id` to identify the paused conversation
4. **Waits** for a follow-up request with the human's decision

### API Approval Flow

**Step 1: Send a message that triggers a sensitive tool**

```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Create a file named report.md with info about LangChain"}],
    "stream": false,
    "thread_id": "conversation-1"
  }'
```

**Response** (agent paused, waiting for approval):

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "{\"question\": \"Do you approve the following tool call(s)?\", \"tool_calls\": [\"Tool: create_file, Args: {...}\"], \"options\": [\"yes\", \"no\"]}"
      },
      "finish_reason": "pending_approval"
    }
  ],
  "thread_id": "conversation-1"
}
```

**Step 2: Approve or reject the tool call**

```bash
# Approve
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": ""}],
    "thread_id": "conversation-1",
    "approval": "yes"
  }'

# Or reject
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": ""}],
    "thread_id": "conversation-1",
    "approval": "no"
  }'
```

### Thread-Based Conversations

Each conversation requires a `thread_id` for HITL to work:

- The `thread_id` identifies the paused graph state
- You **must** use the same `thread_id` when sending the approval
- State is stored in-memory using LangGraph's `MemorySaver` checkpointer
- State does not persist across server restarts (use a database checkpointer for production)

### Customization

Edit `src/human_in_the_loop/agent.py` to add more sensitive tools to the interrupt list:

```python
hitl_middleware = HumanInTheLoopMiddleware(
    interrupt_on={
        "create_file": True,
        "delete_record": True,
    },
)
```

Edit `src/human_in_the_loop/tools.py` to add new tools:

```python
@tool("delete_record", parse_docstring=True)
def delete_record(record_id: str) -> str:
    """Delete a record from the database. Requires human approval."""
    # Implementation here
```

### Architecture

This agent combines three key components:

1. **LangGraph StateGraph**: Custom workflow with conditional routing for safe vs sensitive tools
2. **LangGraph Interrupts**: `interrupt()` pauses execution; `Command(resume=...)` resumes it
3. **ChatOpenAI**: OpenAI-compatible LLM client (connects to Llama-stack or OpenAI)

```
User Input → Agent Node (LLM) → Route Decision
                                   ├── No tools → END
                                   ├── Safe tool → Tool Node → Agent Node (loop)
                                   └── Sensitive tool → Human Approval Node
                                                          ├── interrupt() → PAUSE
                                                          ├── resume("yes") → Tool Node → Agent Node → END
                                                          └── resume("no") → Rejection Message → END
```

### Troubleshooting

**Error: "No user message found in messages list"**

- Solution: Ensure your request includes at least one message with `"role": "user"`

**Approval request returns error**

- Solution: Use the same `thread_id` from the pending approval response
- The graph state must exist in the checkpointer for resume to work

**State lost after server restart**

- The default `MemorySaver` is in-memory only
- For production, use `PostgresSaver` (see `react_with_database_memory` agent for reference)

## Resources

- [LangGraph Interrupts](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [Llama Stack Documentation](https://llama-stack.readthedocs.io/)
- [Ollama Documentation](https://ollama.com/docs)