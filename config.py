"""Configuration: models, settings, routing rules."""
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

# Description string injected into the router's system prompt
MODEL_DESCRIPTIONS: str = "\n".join(
    f'- task_category="{key}": model_id="{cfg.model_id}" — {cfg.description} '
    f'(best for: {', '.join(cfg.best_for)})'
    for key, cfg in MODEL_REGISTRY.items()
    if key != "router"
)
