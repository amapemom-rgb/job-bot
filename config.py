"""Configuration: models, settings, routing rules.

Совместимо с Python 3.10+ (без f-строк с переиспользованием кавычек, PEP 701).
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

# ---------------------------------------------------------------------------
# OpenRouter
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------
@dataclass
class ModelConfig:
    model_id: str
    description: str
    cost_tier: str          # "free" | "paid"
    context_window: int
    best_for: list[str] = field(default_factory=list)


MODEL_REGISTRY: dict[str, ModelConfig] = {
    "router": ModelConfig(
        model_id=os.getenv("ROUTER_MODEL", "google/gemma-4-26b-a4b-it:free"),
        description="Fast routing decisions — decides which model to use",
        cost_tier="free",
        context_window=262144,
        best_for=["routing", "classification"],
    ),
    "chat": ModelConfig(
        model_id=os.getenv("CHAT_MODEL", "google/gemma-4-26b-a4b-it:free"),
        description="Simple conversation, quick Q&A",
        cost_tier="free",
        context_window=262144,
        best_for=["chat", "simple_questions", "greetings"],
    ),
    "analyze": ModelConfig(
        model_id=os.getenv("ANALYZE_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"),
        description="Job evaluation, matching analysis, reasoning",
        cost_tier="free",
        context_window=1048576,
        best_for=["job_evaluation", "matching", "analysis", "comparison"],
    ),
    "write": ModelConfig(
        model_id=os.getenv("WRITE_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
        description="CV writing, cover letters, professional text",
        cost_tier="free",
        context_window=1048576,
        best_for=["cv_writing", "cover_letter", "professional_writing"],
    ),
    "code": ModelConfig(
        model_id=os.getenv("CODE_MODEL", "qwen/qwen3-coder:free"),
        description="Code generation, technical tasks",
        cost_tier="free",
        context_window=1048576,
        best_for=["code", "technical", "scripts"],
    ),
    "premium": ModelConfig(
        model_id="anthropic/claude-sonnet-4-5",
        description="Highest quality fallback for critical tasks",
        cost_tier="paid",
        context_window=200000,
        best_for=["critical", "complex", "premium"],
    ),
}

DEFAULT_CATEGORY = "chat"

# Цепочки фолбэка: если выбранная модель упала (rate limit бесплатных
# моделей OpenRouter — обычное дело), пробуем следующую.
# premium НЕ включён в автофолбэк бесплатных категорий — платная модель
# не должна включаться без явного решения.
FALLBACK_CHAIN: dict[str, list[str]] = {
    "chat": ["chat", "analyze"],
    "analyze": ["analyze", "chat"],
    "write": ["write", "analyze", "chat"],
    "code": ["code", "chat"],
    "premium": ["premium", "write", "chat"],
}


def resolve_model(task_category: str) -> str:
    """Маппинг категории → model_id на стороне сервера.

    LLM-роутер возвращает только категорию; строку модели он не пишет
    (опечатки и «творческий» выбор платной модели исключены).
    Неизвестная категория → chat.
    """
    key = (task_category or "").strip().lower()
    cfg = MODEL_REGISTRY.get(key)
    if cfg is None or key == "router":
        cfg = MODEL_REGISTRY[DEFAULT_CATEGORY]
    return cfg.model_id


def fallback_models(task_category: str) -> list[str]:
    """Список model_id для категории: основная + фолбэки, без дублей."""
    key = (task_category or "").strip().lower()
    categories = FALLBACK_CHAIN.get(key, [DEFAULT_CATEGORY])
    seen: set[str] = set()
    out: list[str] = []
    for cat in categories:
        mid = resolve_model(cat)
        if mid not in seen:
            seen.add(mid)
            out.append(mid)
    return out


# Description string injected into the router's system prompt.
# Собрано циклом, а не вложенной f-строкой — синтаксис валиден на Python 3.10+.
_desc_lines: list[str] = []
for _key, _cfg in MODEL_REGISTRY.items():
    if _key == "router":
        continue
    _best = ", ".join(_cfg.best_for)
    _desc_lines.append(
        '- task_category="{key}" — {desc} (best for: {best})'.format(
            key=_key, desc=_cfg.description, best=_best
        )
    )
MODEL_DESCRIPTIONS: str = "\n".join(_desc_lines)
