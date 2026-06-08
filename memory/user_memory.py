"""User profile and conversation history — stored as JSON files.

MVP storage: one JSON file per user in data/users/.
Can be swapped for a database (PostgreSQL, Redis) later without changing the API.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("data/users")
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_HISTORY = 20   # conversation messages to keep
MAX_JOBS = 50      # job search history entries to keep


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
    """Persist user memory to disk."""
    memory.profile.updated_at = _now()
    # Trim to limits
    memory.conversation_history = memory.conversation_history[-MAX_HISTORY:]
    memory.job_search_history = memory.job_search_history[-MAX_JOBS:]
    data = {
        "profile": asdict(memory.profile),
        "conversation_history": memory.conversation_history,
        "job_search_history": memory.job_search_history,
    }
    _path(memory.profile.user_id).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_message(memory: UserMemory, role: str, content: str) -> None:
    """Append a message to conversation history."""
    memory.conversation_history.append(
        {"role": role, "content": content, "ts": _now()}
    )


def update_profile_field(memory: UserMemory, field_name: str, value: object) -> None:
    """Update a single field in user profile."""
    if hasattr(memory.profile, field_name):
        setattr(memory.profile, field_name, value)
