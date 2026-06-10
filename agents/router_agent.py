"""ROUTER agent — uses a cheap LLM to decide which model should handle the task.

Изменения после ревью:
- Роутер возвращает только task_category. model_id резолвится на сервере
  (config.resolve_model) — LLM не пишет строки моделей и не может ни
  опечататься, ни самовольно выбрать платную модель.
- Роутер заодно извлекает данные профиля, явно сообщённые пользователем
  («Я Python-разработчик, ищу удалёнку в Европе») — один LLM-вызов вместо двух.
- При падении роутера возвращается безопасный дефолт (chat), бот не умирает.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    MODEL_REGISTRY,
    MODEL_DESCRIPTIONS,
    DEFAULT_CATEGORY,
    resolve_model,
)

log = logging.getLogger(__name__)

VALID_CATEGORIES = {"chat", "analyze", "write", "code", "premium"}


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------
class ProfileUpdates(BaseModel):
    """Данные профиля, ЯВНО сообщённые пользователем в этом сообщении.

    Заполнять только то, что пользователь сказал сам. Не выдумывать.
    """
    profession: str | None = None
    skills: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    salary_expectation: str | None = None
    languages: list[str] = Field(default_factory=list)


class RouterDecision(BaseModel):
    task_category: str = Field(
        description="One of: chat, analyze, write, code, premium"
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
    profile_updates: ProfileUpdates | None = Field(
        default=None,
        description="Profile data the user EXPLICITLY stated in this message, else null",
    )

    @property
    def model_id(self) -> str:
        """model_id резолвится сервером из категории — не из вывода LLM."""
        return resolve_model(self.task_category)


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
Your job: analyze the user's message, pick a task_category, and extract any profile
data the user explicitly stated about themselves.

Available categories:
{MODEL_DESCRIPTIONS}

Routing rules:
- Greetings, small talk, simple questions → chat
- "найди вакансию", "ищи работу", "подходит ли мне", job URL → analyze
- "напиши резюме", "составь cover letter", "обнови CV" → write
- Technical / code requests → code
- Use premium ONLY if complexity >= 9 AND the task is business-critical

Profile extraction rules:
- Fill profile_updates ONLY with facts the user explicitly stated about themselves
  (profession, skills, locations, salary expectation, languages).
- If the user stated nothing about themselves → profile_updates = null.
- Never invent or guess profile data.

Always return a valid RouterDecision JSON. Never add explanation outside JSON."""

router_agent: Agent[None, RouterDecision] = Agent(
    model=_router_model,
    result_type=RouterDecision,
    system_prompt=ROUTER_SYSTEM_PROMPT,
)


def _safe_default(reason: str) -> RouterDecision:
    log.warning("Router fallback to default category: %s", reason)
    return RouterDecision(
        task_category=DEFAULT_CATEGORY,
        task_summary="Не удалось классифицировать запрос — обычный чат",
        complexity=3,
        requires_user_profile=False,
        profile_updates=None,
    )


async def route(user_message: str) -> RouterDecision:
    """Classify user_message and return a routing decision.

    Любая ошибка роутера (rate limit, невалидный JSON, сеть) не валит бота —
    возвращаем безопасный дефолт.
    """
    try:
        result = await router_agent.run(user_message)
        decision = result.data
    except Exception as exc:  # noqa: BLE001 — деградируем мягко
        return _safe_default(repr(exc))

    # Валидация категории: LLM мог вернуть что-то своё
    if decision.task_category.strip().lower() not in VALID_CATEGORIES:
        decision.task_category = DEFAULT_CATEGORY

    return decision
