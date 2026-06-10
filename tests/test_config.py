"""Тесты config: серверная резолюция моделей, фолбэк-цепочки, сборка описаний."""

from config import (
    MODEL_REGISTRY,
    MODEL_DESCRIPTIONS,
    resolve_model,
    fallback_models,
)


def test_resolve_known_categories():
    assert resolve_model("write") == MODEL_REGISTRY["write"].model_id
    assert resolve_model("analyze") == MODEL_REGISTRY["analyze"].model_id
    assert resolve_model("ANALYZE ") == MODEL_REGISTRY["analyze"].model_id  # нормализация


def test_resolve_unknown_falls_back_to_chat():
    assert resolve_model("nonsense") == MODEL_REGISTRY["chat"].model_id
    assert resolve_model("") == MODEL_REGISTRY["chat"].model_id
    assert resolve_model(None) == MODEL_REGISTRY["chat"].model_id


def test_resolve_router_not_exposed():
    """Категория 'router' — служебная, юзерские задачи туда не идут."""
    assert resolve_model("router") == MODEL_REGISTRY["chat"].model_id


def test_fallback_chain_unique_and_nonempty():
    for cat in ("chat", "analyze", "write", "code", "premium"):
        chain = fallback_models(cat)
        assert chain, cat
        assert len(chain) == len(set(chain)), f"дубли в цепочке {cat}"
        assert chain[0] == resolve_model(cat)


def test_free_categories_never_fall_back_to_paid():
    paid = {cfg.model_id for cfg in MODEL_REGISTRY.values() if cfg.cost_tier == "paid"}
    for cat in ("chat", "analyze", "write", "code"):
        assert not (set(fallback_models(cat)) & paid), (
            f"бесплатная категория {cat} не должна фолбэчиться на платную модель"
        )


def test_model_descriptions_built():
    assert 'task_category="write"' in MODEL_DESCRIPTIONS
    assert 'task_category="router"' not in MODEL_DESCRIPTIONS
    assert "best for:" in MODEL_DESCRIPTIONS
