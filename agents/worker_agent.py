"""WORKER agent — executes the actual task using the model chosen by ROUTER.

Изменения после ревью:
- run_worker принимает СПИСОК моделей и пробует по очереди (фолбэк при
  rate limit / отказе бесплатных моделей OpenRouter).
- В deps добавлен job_context — текст вакансии, заскрапленный ботом.
  Worker'у прямо запрещено выдумывать содержимое страниц по URL.
- В профиль-промпт добавлен фрагмент CV, если загружено.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from memory.user_memory import UserProfile

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dependencies injected into the worker at runtime
# ---------------------------------------------------------------------------
@dataclass
class WorkerDeps:
    user_id: int
    profile: UserProfile
    conversation_history: list[dict[str, str]]  # [{"role": ..., "content": ...}]
    job_context: str = ""   # текст вакансии, заскрапленный ботом (если была ссылка)


# ---------------------------------------------------------------------------
# Worker factory
# ---------------------------------------------------------------------------
WORKER_SYSTEM_PROMPT = """You are a professional AI assistant specializing in job search.
You help users find jobs, evaluate vacancies, write CVs and cover letters.

Be concise, practical, and respond in the same language the user writes in.
Default language: Russian.

When writing CVs or cover letters, always tailor them to the specific job description.
When evaluating a vacancy, give an honest assessment: match %, pros, cons, salary estimate.

CRITICAL: You CANNOT open URLs. If the user sent a link and the message contains
a [Job posting content] block — use it. If there is NO such block, say honestly
that you could not read the page and ask the user to paste the job text.
NEVER invent the content of a web page."""


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
        if p.cv_text:
            parts.append(f"CV (excerpt):\n{p.cv_text[:1500]}")
        parts.append("--- End Profile ---")
        return "\n".join(parts)

    return agent


def _build_message(user_message: str, deps: WorkerDeps) -> str:
    """Собирает сообщение: история + текст вакансии + текущий запрос."""
    blocks: list[str] = []

    if deps.conversation_history:
        recent = deps.conversation_history[-6:]  # last 3 exchanges
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in recent
        )
        blocks.append(f"[Recent conversation]\n{history_text}")

    if deps.job_context:
        blocks.append(f"[Job posting content]\n{deps.job_context}")

    blocks.append(f"[Current message]\n{user_message}")
    return "\n\n".join(blocks)


async def run_worker(
    model_ids: list[str],
    user_message: str,
    deps: WorkerDeps,
) -> tuple[str, str]:
    """Run a worker, trying models in order. Returns (reply, model_id_used).

    Бесплатные модели OpenRouter регулярно отдают 429/5xx — пробуем цепочку.
    """
    full_message = _build_message(user_message, deps)

    last_exc: Exception | None = None
    for model_id in model_ids:
        try:
            worker = create_worker(model_id)
            result = await worker.run(full_message, deps=deps)
            return result.data, model_id
        except Exception as exc:  # noqa: BLE001 — пробуем следующую модель
            log.warning("Worker model %s failed: %r — trying next", model_id, exc)
            last_exc = exc

    raise last_exc or RuntimeError("Нет доступных моделей")
