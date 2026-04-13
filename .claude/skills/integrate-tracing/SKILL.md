# Integrate MLflow Tracing into an Agent Template

> **Usage:** `/project:integrate-tracing <framework> <agent_path>`
> **Example:** `/project:integrate-tracing autogen agents/autogen/chat_agent`

You are integrating MLflow tracing into a new agent template in this repository. This is the orchestrator skill that coordinates the full end-to-end process by following a structured sequence of steps, deferring to reference skills for each step.

## Input

The framework name and agent path are: $ARGUMENTS

Expected format: `<framework> <agent_path>`
Example: `autogen agents/autogen/chat_agent`

If either is missing, ask the user for both.

## Before You Start

Read `tracing.md` at the repo root for full context on the tracing architecture, design principles, and how the existing four agents integrate with MLflow. This is essential background.

## Workflow

**IMPORTANT: You must follow these steps in exact sequential order (1 → 2 → 3 → ... → 9). Do not skip ahead, reorder, or combine steps. Each step depends on the output of previous steps — especially the autolog report from Step 1, which drives decisions in Steps 4, 5, 6, and 7. Complete each step fully before moving to the next.**

**IMPORTANT: Always create a demo agent first (Step 2) and implement all tracing and testing on the demo copy (Steps 3–7). Only after everything works correctly on the demo — traces land in MLflow, spans are correct, both streaming and non-streaming paths are verified — apply the same changes to the actual agent template (Steps 4–9). Never modify the real agent template until the demo is fully working.**

### Step 1: Check Autolog Support

**Goal**: Determine what MLflow autolog covers for this framework.

Follow the `check-autolog-support` skill with the framework name. This will produce an autolog support report classifying the framework as:

- **Level A** — Full autolog (like LangGraph, LlamaIndex)
- **Level B** — Partial autolog (like CrewAI)
- **Level C** — No framework autolog (like Vanilla Python)

Save the report — it drives all subsequent decisions.

### Step 2: Create a Demo Agent

**Goal**: Create a working demo copy of the agent for testing tracing before modifying the actual agent.

1. Copy the agent directory to `agents/demo/<framework>_<agent_name>_demo/`
2. **Replace dummy tools with proper test tools** — the demo MUST have tools that return meaningful responses so traces can be properly verified. Use these standard demo tools (adapted to the framework's tool format):
   - `search_knowledge_base(query)` — looks up a hardcoded knowledge base dict
   - `search_price(brand)` — returns `"Price of {brand} is $400"`
   - `search_reviews(brand)` — returns `"Reviews of {brand} are good"`
   - `current_time()` — returns current datetime
   - `calculate(query)` — evaluates a math expression
3. Update the tools export (`__init__.py` or equivalent) to include all new tools
4. Update the agent's system prompt to mention the available tools
5. Create a `.env` file with OpenAI credentials and MLflow config for local testing
6. If the agent requires external dependencies (MCP server, vector store, database), add a fallback in the demo's `main.py` so it can run with dummy tools when the dependency is unavailable

This step is critical — without proper tools, you cannot verify that tool spans appear in traces.

### Step 3: Understand the Agent's Code

**Goal**: Map the agent's architecture before making changes.

Read these files in the agent directory:
- `README.md` — What the agent does, its architecture, tools, and any framework-specific details
- `main.py` — FastAPI app, lifespan, `_handle_chat`, `_handle_stream`
- `src/<package>/agent.py` — Agent class/factory, how tools are registered
- `src/<package>/tools.py` — Tool definitions
- `pyproject.toml` — Package name and dependencies

Identify:
- The Python package name (from `pyproject.toml` or `src/` directory)
- How the agent initializes (closure pattern, class instantiation, etc.)
- How tools are registered (function list, tool objects, decorators)
- Whether streaming creates the agent differently from non-streaming
- What LLM SDK the framework uses under the hood (OpenAI, LangChain, LiteLLM, etc.)

### Step 4: Create the Tracing Module

**Goal**: Create `tracing.py` with the correct pattern for this framework.

Follow the `create-tracing-module` skill, providing:
- The agent path
- The autolog support report from Step 1

This creates `src/<package>/tracing.py` with:
- Level A: `enable_tracing()` with framework autolog only
- Level B: `enable_tracing()` with framework + provider autolog, plus `wrap_func_with_mlflow_trace()`
- Level C: `enable_tracing()` with provider autolog only, plus `wrap_func_with_mlflow_trace()`

### Step 5: Wire into the FastAPI Lifespan

**Goal**: Connect tracing to the app startup.

Follow the `wire-into-lifespan` skill, providing:
- The agent path
- The package name
- The coverage level

This adds the import and `enable_tracing()` call to `main.py`.

### Step 6: Add Manual Tracing (Level B and C only)

**Goal**: Wrap tools and agent entry points with trace spans where autolog doesn't cover.

**Skip this step entirely for Level A** — autolog handles everything.

For Level B or C, follow the `add-manual-tracing` skill, providing:
- The agent path
- The package name
- The coverage level
- What the autolog covers and misses (from the report)

This adds `wrap_func_with_mlflow_trace()` calls for:
- Tool functions/methods → `span_type="tool"`
- Agent entry point → `span_type="agent"`
- Both streaming and non-streaming paths

### Step 7: Verify

**Goal**: Confirm traces land correctly in MLflow.

Read and execute every step in the `verify-traces` skill yourself, which in turn requires you to execute the `review-tracing-code` and `test-tracing` skills. You must do everything hands-on — install MLflow if needed, start the MLflow server, start the agent, send requests, query the MLflow API, inspect spans. Do NOT stop here and tell the user to test manually. Do NOT summarize what the user should do. Execute it all yourself.

After verification, always report these three values to the user:
- **MLflow Server URI** — the URI used to connect to the MLflow server (e.g., `http://localhost:5000`)
- **Experiment Name** — the MLflow experiment name used (e.g., `agentic-rag-experiment`)
- **Test Query** — the exact query sent to the agent during testing (e.g., `"How much does a Lenovo laptop cost?"`)

If verification fails, the report will indicate which step to revisit.

### Step 8: Update .env.example

**Goal**: Add MLflow environment variables to `.env.example` so users know which variables to configure.

Add the following sections to the agent's `.env.example` file (if not already present):

```ini
## LOCAL TRACING

# MLFLOW_TRACKING_URI=
# MLFLOW_EXPERIMENT_NAME=
# MLFLOW_HEALTH_CHECK_TIMEOUT=      # (default is 5s)
# MLFLOW_HTTP_REQUEST_TIMEOUT=      # (default is 120s)
# MLFLOW_HTTP_REQUEST_MAX_RETRIES=

## OPENSHIFT CLUSTER TRACING

# Openshift Cluster
# MLFLOW_TRACKING_URI=
# MLFLOW_TRACKING_TOKEN=
# MLFLOW_EXPERIMENT_NAME=
# MLFLOW_TRACKING_INSECURE_TLS=
# MLFLOW_WORKSPACE=
# MLFLOW_TRACKING_AUTH= # Use Kubernetes service account for authentication (if running inside the cluster)
```

### Step 9: Update README.md

**Goal**: Document tracing setup for both local and OpenShift deployments.

Add these sections to the agent's `README.md` (use an existing agent like `langgraph/react_agent` as reference):

1. **Local Tracing config** — under the Local `.env` configuration section, add a `##### Tracing` subsection with example MLflow env vars:
   ```ini
   MLFLOW_TRACKING_URI="http://localhost:5000"
   MLFLOW_EXPERIMENT_NAME="<Agent Name> Local Experiment"
   MLFLOW_HTTP_REQUEST_TIMEOUT=2
   MLFLOW_HTTP_REQUEST_MAX_RETRIES=0
   ```

2. **OpenShift Tracing config** — under the OpenShift `.env` configuration section, add a `##### Tracing` subsection with:
   - Example env vars (`MLFLOW_TRACKING_URI`, `MLFLOW_TRACKING_TOKEN`, `MLFLOW_EXPERIMENT_NAME`, `MLFLOW_TRACKING_INSECURE_TLS`, `MLFLOW_WORKSPACE`)
   - Notes explaining each variable
   - Three behavioral notes:
     - Tracing is optional; if `MLFLOW_TRACKING_URI` is not set, the app runs without MLflow logging
     - If set but unreachable, the app logs a warning and continues without tracing
     - `MLFLOW_HEALTH_CHECK_TIMEOUT` controls wait time (default: 5s)

3. **Local MLflow install** — in the Local Usage section, after `uv pip install -e .`, add:
   ```bash
   uv pip install "mlflow>=3.10.0"
   ```
   with a note: *Optional: Only required if tracing is enabled*

4. **MLflow server start** — in the Local Usage section, add a step to start the MLflow server:
   ```bash
   mlflow server --port 5000
   ```

## Complete Checklist

All files that must be created or updated when integrating tracing:

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `src/<package>/tracing.py` | **Create** | `enable_tracing()`, health check, autolog, `wrap_func_with_mlflow_trace()` (Level B/C) |
| 2 | `main.py` | **Edit** | Import `enable_tracing`, call it first in `lifespan()` |
| 3 | `main.py` | **Edit** (Level B/C only) | Import `wrap_func_with_mlflow_trace`, wrap tools/agent entry points |
| 4 | `.env.example` | **Edit** | Add local + OpenShift MLflow variable sections |
| 5 | `README.md` | **Edit** | Add local tracing config, OpenShift tracing config, MLflow server start |
| 6 | `pyproject.toml` | **Edit** | Add `tracing = ["mlflow>=3.10.0"]` to `[project.optional-dependencies]` |
| 7 | `Makefile` | **Edit** | Add `$${MLFLOW_TRACKING_URI:+--extra tracing}` to `uv run` in `run` and `run-cli` targets |

## Summary

| Step | Skill | Level A | Level B | Level C |
|------|-------|---------|---------|---------|
| 1. Check autolog | `check-autolog-support` | Run | Run | Run |
| 2. Create demo agent | (inline) | Run | Run | Run |
| 3. Read agent code | (inline) | Run | Run | Run |
| 4. Create tracing.py | `create-tracing-module` | Run | Run | Run |
| 5. Wire into lifespan | `wire-into-lifespan` | Run | Run | Run |
| 6. Add manual tracing | `add-manual-tracing` | **Skip** | Run | Run |
| 7. Verify | `verify-traces` | Run | Run | Run |
| 8. Update .env.example | (inline) | Run | Run | Run |
| 9. Update README.md | (inline) | Run | Run | Run |

## Keeping Skills Up to Date

If at any point during this workflow you deviate from a skill's instructions because they were inaccurate, outdated, or insufficient — and your deviation works — **update the skill file** with what you learned. This includes:

- A step that didn't work as described and needed a different approach
- A new pattern or edge case not covered by the skill
- File paths or function names that have changed
- A new framework behavior that the skill should account for

Also update `tracing.md` at the repo root:

- **Always** add the new framework to the Autolog Coverage Levels table and the Tracing Layers table, so every framework's level is recorded.
- **Always** add a new Framework-Specific Integration section for the agent (like the existing LangGraph, CrewAI, etc. sections), documenting the autolog module used, whether manual tracing was needed, and the resulting span structure.
- Add any new findings, edge cases, or architectural patterns discovered during integration. Keep these short and direct — a few sentences, not paragraphs.
