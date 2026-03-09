from crewai import LLM
from crewai.agents.parser import AgentAction, AgentFinish
from crewai.tools.tool_types import ToolResult

from crewai_web_search.crew import AssistanceAgents


def ai_stream_service(context, base_url=None, model_id=None):
    """Create a deployable AI service that runs the CrewAI web search crew.

    Builds the LLM once, then returns two callables: one for a single
    non-streaming response and one that returns a non-streaming response
    (CrewAI does not support streaming).

    Args:
        context: Object with get_json() used to read the request payload.
        base_url: LLM API base URL (OpenAI-compatible / llama-stack).
        model_id: LLM model id; will be prefixed with 'openai/'.

    Returns:
        Tuple (generate, generate). CrewAI does not support streaming,
        so both entries return the same non-streaming callable.
    """
    from os import getenv

    api_key = getenv("API_KEY", "no-key")

    if base_url and not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    llm = LLM(
        model=f"openai/{model_id}",
        base_url=base_url,
        api_key=api_key,
        temperature=0.7,
    )

    def get_formatted_message(
        crewai_step: AgentAction | AgentFinish | ToolResult,
    ) -> dict | None:
        """Turn a CrewAI step into a display dict (role + content) for the client."""
        if isinstance(crewai_step, AgentAction):
            return {"role": "assistant", "content": crewai_step.result}
        elif isinstance(crewai_step, AgentFinish):
            return {"role": "assistant", "content": crewai_step.output}
        elif isinstance(crewai_step, ToolResult):
            return {"role": "tool", "content": f"\n🔧 Tool Output:\n {crewai_step.result}"}
        return None

    def generate(context) -> dict:
        """Run the crew on the context payload and return a response dict with choices."""
        payload = context.get_json()
        messages = payload.get("messages", [])

        user_question = messages[-1]["content"]
        custom_instruction = ""
        if messages and messages[0].get("role") == "system":
            custom_instruction = messages[0]["content"]

        inputs = {
            "user_prompt": user_question,
            "custom_instruction": custom_instruction,
        }

        intermediate_steps: list = []
        _ = (
            AssistanceAgents(llm=llm, intermediate_steps=intermediate_steps)
            .crew()
            .kickoff(inputs=inputs)
        )

        choices = []
        for i, step in enumerate(intermediate_steps):
            msg = get_formatted_message(step)
            if msg:
                choices.append({"index": i, "message": msg})

        return {
            "headers": {"Content-Type": "application/json"},
            "body": {"choices": choices},
        }

    # CrewAI does not support streaming, so both entries point to generate
    return generate, generate
