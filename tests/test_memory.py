"""Тесты памяти: roundtrip, атомарность, merge профиля, обрезка истории."""

import os

# Каталог данных назначаем ДО импорта модуля
os.environ["JOB_BOT_DATA_DIR"] = os.path.join(
    os.environ.get("TMPDIR", "/tmp"), "job_bot_test_users"
)

from memory import user_memory as mem  # noqa: E402


def _fresh(user_id=111):
    p = mem._path(user_id)
    if p.exists():
        p.unlink()
    return mem.load(user_id)


def test_load_new_user():
    memory = _fresh(101)
    assert memory.profile.user_id == 101
    assert memory.conversation_history == []


def test_save_load_roundtrip():
    memory = _fresh(102)
    memory.profile.profession = "Python developer"
    memory.profile.skills = ["python", "sql"]
    mem.add_message(memory, "user", "привет")
    mem.add_message(memory, "assistant", "здравствуйте")
    mem.save(memory)

    loaded = mem.load(102)
    assert loaded.profile.profession == "Python developer"
    assert loaded.profile.skills == ["python", "sql"]
    assert len(loaded.conversation_history) == 2
    # tmp-файла не осталось (атомарная запись)
    assert not mem._path(102).with_suffix(".json.tmp").exists()


def test_history_trimmed():
    memory = _fresh(103)
    for i in range(50):
        mem.add_message(memory, "user", f"msg {i}")
    mem.save(memory)
    assert len(memory.conversation_history) == mem.MAX_HISTORY


def test_corrupt_file_returns_empty():
    memory = _fresh(104)
    mem.save(memory)
    mem._path(104).write_text("{broken json", encoding="utf-8")
    loaded = mem.load(104)
    assert loaded.profile.user_id == 104


def test_merge_profile_updates_scalars_and_lists():
    memory = _fresh(105)
    memory.profile.skills = ["python"]

    changed = mem.merge_profile_updates(memory, {
        "profession": "Data engineer",
        "skills": ["Python", "Airflow"],   # "Python" — дубль (регистр), "Airflow" — новое
        "preferred_locations": ["Берлин"],
        "salary_expectation": "",          # пустое — не перезаписываем
        "languages": [],
    })

    assert "profession" in changed
    assert memory.profile.profession == "Data engineer"
    assert memory.profile.skills == ["python", "Airflow"]
    assert memory.profile.preferred_locations == ["Берлин"]
    assert memory.profile.salary_expectation == ""
    assert "languages" not in changed


def test_merge_profile_updates_noop():
    memory = _fresh(106)
    changed = mem.merge_profile_updates(memory, {})
    assert changed == []
