"""Тесты utils: URL, экранирование, чанкинг."""

from utils import extract_urls, escape_html, split_message


def test_extract_urls():
    text = "Глянь вакансию https://hh.ru/vacancy/123 и ещё http://example.com/job?id=5"
    urls = extract_urls(text)
    assert urls == ["https://hh.ru/vacancy/123", "http://example.com/job?id=5"]


def test_extract_urls_empty():
    assert extract_urls("просто текст без ссылок") == []
    assert extract_urls("") == []
    assert extract_urls(None) == []


def test_escape_html():
    assert escape_html("a < b & c > d") == "a &lt; b &amp; c &gt; d"
    assert escape_html("") == ""


def test_split_message_short():
    assert split_message("привет") == ["привет"]


def test_split_message_long():
    text = "\n\n".join(f"Абзац {i}: " + "слово " * 100 for i in range(20))
    chunks = split_message(text, limit=1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert len(chunks) > 1
    # Ничего не потеряли (с точностью до обрезанных пробелов на стыках)
    rejoined = "".join(c.replace(" ", "").replace("\n", "") for c in chunks)
    original = text.replace(" ", "").replace("\n", "")
    assert rejoined == original


def test_split_message_no_spaces():
    text = "x" * 9000
    chunks = split_message(text, limit=4000)
    assert all(len(c) <= 4000 for c in chunks)
    assert "".join(chunks) == text
