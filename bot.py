"""Telegram bot — main entry point.

Flow per user message:
  1. Load user memory (profile + history)
  2. ROUTER agent classifies message and picks the right model
  3. WORKER agent (chosen model) executes the task with user context
  4. Save updated memory
  5. Send reply to Telegram

Errors are caught and reported to ADMIN_CHAT_ID.
"""
from __future__ import annotations

import asyncio
import logging
import traceback

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_TOKEN, ADMIN_CHAT_ID
from agents.router_agent import route, RouterDecision
from agents.worker_agent import run_worker, WorkerDeps
from memory import user_memory as mem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def notify_admin(text: str) -> None:
    """Send alert to admin Telegram chat."""
    if not ADMIN_CHAT_ID:
        return
    try:
        await bot.send_message(ADMIN_CHAT_ID, f"🤖 <b>job-bot alert</b>\n\n{text}")
    except Exception:
        pass


async def typing(chat_id: int) -> None:
    await bot.send_chat_action(chat_id, "typing")


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    memory = mem.load(user_id)

    if not memory.profile.name:
        memory.profile.user_id = user_id
        memory.profile.name = message.from_user.full_name
        memory.profile.username = message.from_user.username or ""
        mem.save(memory)

    await message.answer(
        f"👋 Привет, <b>{memory.profile.name}</b>!\n\n"
        "Я помогу найти работу, оценить вакансию и написать резюме.\n\n"
        "<b>Что умею:</b>\n"
        "• Анализировать вакансии по ссылке\n"
        "• Писать CV и cover letter под конкретную вакансию\n"
        "• Отвечать на вопросы о поиске работы\n\n"
        "Просто напиши что тебе нужно, или отправь ссылку на вакансию.\n"
        "Команды: /profile /apply /status /help"
    )


# ---------------------------------------------------------------------------
# /profile
# ---------------------------------------------------------------------------
@dp.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    memory = mem.load(message.from_user.id)
    p = memory.profile

    lines = ["<b>👤 Твой профиль:</b>\n"]
    lines.append(f"Имя: {p.name or '—'}")
    lines.append(f"Профессия: {p.profession or '—'}")
    lines.append(f"Навыки: {', '.join(p.skills) if p.skills else '—'}")
    lines.append(f"Локации: {', '.join(p.preferred_locations) if p.preferred_locations else '—'}")
    lines.append(f"Зарплата: {p.salary_expectation or '—'}")
    lines.append(f"Языки: {', '.join(p.languages) if p.languages else '—'}")
    lines.append(f"CV загружено: {'✅' if p.cv_text else '❌'}")
    lines.append(
        "\nЧтобы обновить профиль — просто напиши, например:\n"
        "<i>'Я Python разработчик, ищу удалённую работу в Европе'</i>"
    )
    await message.answer("\n".join(lines))


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------
@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    from config import MODEL_REGISTRY
    lines = ["<b>🟢 Bot status: Online</b>\n"]
    lines.append(f"Router: <code>{MODEL_REGISTRY['router'].model_id}</code>\n")
    lines.append("<b>Available models:</b>")
    for key, cfg in MODEL_REGISTRY.items():
        tier = "🆓" if cfg.cost_tier == "free" else "💰"
        lines.append(f"{tier} <code>{key}</code>: {cfg.description}")
    await message.answer("\n".join(lines))


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------
@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>📖 Команды:</b>\n\n"
        "/start — начало работы\n"
        "/profile — мой профиль\n"
        "/apply [URL] — написать резюме под вакансию\n"
        "/status — статус бота и модели\n"
        "/help — эта справка\n\n"
        "<b>Или просто напиши:</b>\n"
        "• Ссылку на вакансию → анализ + оценка\n"
        "• 'Напиши резюме для...' → готовый текст\n"
        "• 'Я ищу работу в...' → обновлю твой профиль\n"
        "• Любой вопрос о поиске работы"
    )


# ---------------------------------------------------------------------------
# /apply — shortcut: generate CV for a job URL
# ---------------------------------------------------------------------------
@dp.message(Command("apply"))
async def cmd_apply(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи URL вакансии: <code>/apply https://...</code>")
        return
    # Delegate to main handler with the URL as text
    await handle_text(message)


# ---------------------------------------------------------------------------
# Main text handler — ROUTER → WORKER pipeline
# ---------------------------------------------------------------------------
@dp.message(F.text)
async def handle_text(message: Message) -> None:
    user_id = message.from_user.id
    user_text = message.text or ""

    log.info("[%d] → %s", user_id, user_text[:80])

    memory = mem.load(user_id)
    if not memory.profile.user_id:
        memory.profile.user_id = user_id
        memory.profile.name = message.from_user.full_name

    await typing(message.chat.id)

    try:
        # Step 1 — ROUTER: classify + pick model
        decision: RouterDecision = await route(user_text)
        log.info(
            "[%d] router → category=%s model=%s complexity=%d",
            user_id, decision.task_category, decision.model_id, decision.complexity,
        )

        await typing(message.chat.id)  # keep typing indicator alive

        # Step 2 — WORKER: execute with right model
        deps = WorkerDeps(
            user_id=user_id,
            profile=memory.profile,
            conversation_history=memory.conversation_history,
        )
        reply = await run_worker(
            model_id=decision.model_id,
            user_message=user_text,
            deps=deps,
        )

        # Step 3 — Save conversation
        mem.add_message(memory, "user", user_text)
        mem.add_message(memory, "assistant", reply)
        mem.save(memory)

        # Step 4 — Reply (model tag for debugging, remove in production)
        short_model = decision.model_id.split("/")[-1].split(":")[0]
        footer = f"\n\n<i>🤖 {short_model}</i>"
        await message.answer(reply + footer)

    except Exception:
        error_text = traceback.format_exc()
        log.error("[%d] error:\n%s", user_id, error_text)
        await notify_admin(
            f"User {user_id} (@{message.from_user.username})\n"
            f"Msg: {user_text[:200]}\n\n"
            f"<pre>{error_text[:1000]}</pre>"
        )
        await message.answer(
            "⚠️ Что-то пошло не так. Попробуй ещё раз или напиши позже.\n"
            "Ошибка уже отправлена мне на проверку."
        )


# ---------------------------------------------------------------------------
# Document handler — CV upload
# ---------------------------------------------------------------------------
@dp.message(F.document)
async def handle_document(message: Message) -> None:
    doc = message.document
    if not doc.file_name.lower().endswith((".pdf", ".docx", ".txt")):
        await message.answer("Поддерживаются форматы: PDF, DOCX, TXT")
        return
    await message.answer(
        f"📄 Получил файл: <b>{doc.file_name}</b>\n\n"
        "Чтобы я мог использовать твоё резюме при написании cover letter — "
        "скопируй текст резюме и отправь его сообщением."
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
async def set_commands() -> None:
    await bot.set_my_commands([
        BotCommand(command="start",   description="Начать работу"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="apply",   description="Резюме под вакансию"),
        BotCommand(command="status",  description="Статус бота"),
        BotCommand(command="help",    description="Помощь"),
    ])


async def main() -> None:
    log.info("Starting job-bot...")
    await set_commands()
    await notify_admin("✅ job-bot запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
