"""ROUTER agent — uses a cheap LLM to decide which model should handle the task.

Variant B (smart): the router is itself an AI that returns a structured
RouterDecision. No hand-coded if/else logic — the LLM picks the right tool.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    MODEL_REGISTRY,
    MODEL_DESCRIPTIONS,
)


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------
class RouterDecision(BaseModel):
    task_category: str = Field(
        description="One of: chat, analyze, write, code, premium"
    )
    model_id: str = Field(
        description="Exact OpenRouter model string to pass to the WORKER"
    )
    task_summary: str = Field(
        description="One sentence summary of what the user wants (in Russian)"
    )
    complexity: int = Field(
        ge=1, le=10,
        description="Task complexity: 1=trivial, 10=very complex"
    )
    requires_user_profile: bool = Field(
        description="True if the task needs the user's CV/profile to answer well"
    )


# ---------------------------------------------------------------------------
# Router agent
# ---------------------------------------------------------------------------
def _make_openrouter_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/amapemom-rgb/job-bot",
            "X-Title": "job-bot",
        },
    )


_router_model = OpenAIModel(
    MODEL_REGISTRY["router"].model_id,
    openai_client=_make_openrouter_client(),
)

ROUTER_SYSTEM_PROMPT = f"""You are a routing agent for an AI-powered job search Telegram bot.
Your ONLY job: analyze the user's message and decide which AI model should handle it.

Available models (choose task_category and copy the matching model_id exactly):
{MODEL_DESCRIPTIONS}

Routing rules:
- Greetings, small talk, simple questions → chat
- "найди вакансию", "ищи работу", "подходит ли мне" → analyze
- "напиши резюме", "составь cover letter", "обнови CV" → write
- Technical / code requests → code
- Use premium ONLY if complexity >= 9 AND the task is business-critical

Always return a valid RouterDecision JSON. Never add explanation outside JSON."""

router_agent: Agent[None, RouterDecision] = Agent(
    model=_router_model,
    result_type=RouterDecision,
    system_prompt=ROUTER_SYSTEM_PROMPT,
)


async def route(user_message: str) -> RouterDecision:
    """Classify user_message and return a routing decision."""
    result = await router_agent.run(user_message)
    return result.data
