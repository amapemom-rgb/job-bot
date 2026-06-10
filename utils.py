"""Pure helpers: URL extraction, Telegram-safe output, message chunking.

Без внешних зависимостей — легко тестируется.
"""
from __future__ import annotations

import html
import re

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

# Telegram limit is 4096; keep headroom for footer/markup
CHUNK_LIMIT = 4000


def extract_urls(text: str) -> list[str]:
    """Все http(s)-ссылки из текста."""
    return URL_RE.findall(text or "")


def escape_html(text: str) -> str:
    """Экранирование <, >, & — сырой вывод LLM нельзя слать с ParseMode.HTML."""
    return html.escape(text or "", quote=False)


def split_message(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Разбивка длинного текста на куски ≤ limit.

    Telegram падает на сообщениях > 4096 символов. Режем по абзацам,
    затем по строкам, затем по словам, в крайнем случае — жёстко.
    """
    text = text or ""
    chunks: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks
