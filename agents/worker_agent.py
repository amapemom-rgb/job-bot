"""WORKER agent — executes the actual task using the model chosen by ROUTER.

A fresh agent is created per request so it can use any model dynamically.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from memory.user_memory import UserProfile


# ---------------------------------------------------------------------------
# Dependencies injected into the worker at runtime
# ---------------------------------------------------------------------------
@dataclass
class WorkerDeps:
    user_id: int
    profile: UserProfile
    conversation_history: list[dict[str, str]]  # [{"role": ..., "content": ...}]


# ---------------------------------------------------------------------------
# Worker factory
# ---------------------------------------------------------------------------
WORKER_SYSTEM_PROMPT = """You are a professional AI assistant specializing in job search.
You help users find jobs, evaluate vacancies, write CVs and cover letters.

Be concise, practical, and respond in the same language the user writes in.
Default language: Russian.

When writing CVs or cover letters, always tailor them to the specific job description.
When evaluating a vacancy, give an honest assessment: match %, pros, cons, salary estimate."""


def create_worker(model_id: str) -> Agent[WorkerDeps, str]:
    """Return a fresh Pydantic AI agent using the given OpenRouter model."""
    client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/amapemom-rgb/job-bot",
            "X-Title": "job-bot",
        },
    )
    model = OpenAIModel(model_id, openai_client=client)

    agent: Agent[WorkerDeps, str] = Agent(
        model=model,
        result_type=str,
        deps_type=WorkerDeps,
        system_prompt=WORKER_SYSTEM_PROMPT,
    )

    @agent.system_prompt
    async def inject_profile(ctx: RunContext[WorkerDeps]) -> str:
        """Dynamically append user profile to system prompt."""
        p = ctx.deps.profile
        if not p.name:
            return ""
        parts = ["\n--- User Profile (use this to personalize responses) ---"]
        parts.append(f"Name: {p.name}")
        if p.profession:
            parts.append(f"Profession: {p.profession}")
        if p.skills:
            parts.append(f"Skills: {', '.join(p.skills)}")
        if p.preferred_locations:
            parts.append(f"Preferred locations: {', '.join(p.preferred_locations)}")
        if p.salary_expectation:
            parts.append(f"Salary expectation: {p.salary_expectation}")
        if p.languages:
            parts.append(f"Languages: {', '.join(p.languages)}")
        if p.notes:
            parts.append(f"Additional notes: {p.notes}")
        parts.append("--- End Profile ---")
        return "\n".join(parts)

    return agent


async def run_worker(
    model_id: str,
    user_message: str,
    deps: WorkerDeps,
) -> str:
    """Run a worker agent and return the text response."""
    worker = create_worker(model_id)

    # Prepend recent conversation history for context
    if deps.conversation_history:
        recent = deps.conversation_history[-6:]  # last 3 exchanges
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in recent
        )
        user_message = (
            f"[Recent conversation]\n{history_text}\n"
            f"\n[Current message]\n{user_message}"
        )

    result = await worker.run(user_message, deps=deps)
    return result.data
