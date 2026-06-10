"""User profile and conversation history — stored as JSON files.

MVP storage: one JSON file per user in data/users/ (путь настраивается
через JOB_BOT_DATA_DIR). Запись атомарная (tmp + os.replace), чтобы
параллельное сообщение не оставило битый JSON.

Конкурентный доступ из нескольких хендлеров сериализуется per-user
локами на стороне bot.py.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.getenv("JOB_BOT_DATA_DIR", "data/users"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_HISTORY = 20   # conversation messages to keep
MAX_JOBS = 50      # job search history entries to keep

# Поля профиля, которые можно обновлять из извлечённых роутером данных
_SCALAR_FIELDS = ("profession", "salary_expectation")
_LIST_FIELDS = ("skills", "preferred_locations", "languages")


@dataclass
class UserProfile:
    user_id: int = 0
    name: str = ""
    username: str = ""
    profession: str = ""
    skills: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)
    salary_expectation: str = ""
    languages: list[str] = field(default_factory=list)
    cv_text: str = ""    # raw text of uploaded CV
    notes: str = ""      # free-form notes about the user's preferences
    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())


@dataclass
class UserMemory:
    profile: UserProfile = field(default_factory=UserProfile)
    conversation_history: list[dict] = field(default_factory=list)
    job_search_history: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(user_id: int) -> Path:
    return DATA_DIR / f"{user_id}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def load(user_id: int) -> UserMemory:
    """Load user memory. Returns empty memory if user is new."""
    p = _path(user_id)
    if not p.exists():
        return UserMemory(profile=UserProfile(user_id=user_id))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        profile = UserProfile(**data.get("profile", {}))
        return UserMemory(
            profile=profile,
            conversation_history=data.get("conversation_history", []),
            job_search_history=data.get("job_search_history", []),
        )
    except Exception:
        return UserMemory(profile=UserProfile(user_id=user_id))


def save(memory: UserMemory) -> None:
    """Persist user memory to disk (atomic: tmp + os.replace)."""
    memory.profile.updated_at = _now()
    # Trim to limits
    memory.conversation_history = memory.conversation_history[-MAX_HISTORY:]
    memory.job_search_history = memory.job_search_history[-MAX_JOBS:]
    data = {
        "profile": asdict(memory.profile),
        "conversation_history": memory.conversation_history,
        "job_search_history": memory.job_search_history,
    }
    target = _path(memory.profile.user_id)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(tmp, target)


def add_message(memory: UserMemory, role: str, content: str) -> None:
    """Append a message to conversation history."""
    memory.conversation_history.append(
        {"role": role, "content": content, "ts": _now()}
    )


def update_profile_field(memory: UserMemory, field_name: str, value: object) -> None:
    """Update a single field in user profile."""
    if hasattr(memory.profile, field_name):
        setattr(memory.profile, field_name, value)


def merge_profile_updates(memory: UserMemory, updates: dict) -> list[str]:
    """Вливает извлечённые роутером данные профиля.

    Скаляры перезаписываются непустыми значениями, списки дополняются
    без дублей. Возвращает список изменённых полей.
    """
    p = memory.profile
    changed: list[str] = []

    for key in _SCALAR_FIELDS:
        val = updates.get(key)
        if isinstance(val, str):
            val = val.strip()
        if val and val != getattr(p, key):
            setattr(p, key, val)
            changed.append(key)

    for key in _LIST_FIELDS:
        vals = updates.get(key) or []
        current = getattr(p, key)
        current_lower = {str(v).lower() for v in current}
        new_items = [
            str(v).strip() for v in vals
            if v and str(v).strip() and str(v).strip().lower() not in current_lower
        ]
        if new_items:
            current.extend(new_items)
            changed.append(key)

    return changed
