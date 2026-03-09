import asyncio
from contextlib import asynccontextmanager
from os import getenv

from crewai import LLM
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from crewai_web_search.crew import AssistanceAgents


class ChatRequest(BaseModel):
    """Incoming chat request body for the /chat endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Structured chat response."""

    answer: str
    steps: list[str]


# Global LLM instance
llm = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the CrewAI LLM on startup."""
    global llm

    base_url = getenv("BASE_URL")
    model_id = getenv("MODEL_ID")
    api_key = getenv("API_KEY", "no-key")

    if base_url and not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    llm = LLM(
        model=f"openai/{model_id}",
        base_url=base_url,
        api_key=api_key,
        temperature=0.7,
    )

    yield

    llm = None


app = FastAPI(
    title="CrewAI Web Search Agent API",
    description="FastAPI service for CrewAI Web Search Agent",
    lifespan=lifespan,
)


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint that runs the CrewAI crew and returns the response."""
    global llm

    if llm is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        inputs = {
            "user_prompt": request.message,
            "custom_instruction": "",
        }

        intermediate_steps: list = []
        crew = AssistanceAgents(
            llm=llm, intermediate_steps=intermediate_steps
        ).crew()

        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        steps = []
        for step in intermediate_steps:
            from crewai.agents.parser import AgentAction, AgentFinish
            from crewai.tools.tool_types import ToolResult

            if isinstance(step, AgentAction):
                steps.append(f"[action] {step.result}")
            elif isinstance(step, AgentFinish):
                steps.append(f"[finish] {step.output}")
            elif isinstance(step, ToolResult):
                steps.append(f"[tool] {step.result}")

        return ChatResponse(answer=str(result), steps=steps)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@app.get("/health")
async def health():
    """Return service health status."""
    return {"status": "healthy", "agent_initialized": llm is not None}


if __name__ == "__main__":
    import uvicorn

    port = int(getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
