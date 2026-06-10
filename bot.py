"""Telegram bot — main entry point.

Flow per user message:
  1. Per-user lock (защита от гонок параллельных сообщений)
  2. Если в сообщении ссылка — скрапим вакансию (scrape_url)
  3. ROUTER agent: категория задачи + извлечение данных профиля
  4. WORKER agent (модель по категории, с фолбэк-цепочкой) выполняет задачу
  5. Сохраняем память, отвечаем (HTML-экранирование + чанкинг под лимит 4096)

Errors are caught and reported to ADMIN_CHAT_ID (текст сообщения усечён).
"""
from __future__ import annotations

import asyncio
import logging
import traceback
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_TOKEN, ADMIN_CHAT_ID, fallback_models
from agents.router_agent import route, RouterDecision
from agents.worker_agent import run_worker, WorkerDeps
from memory import user_memory as mem
from jobs.scraper import scrape_url
from utils import extract_urls, escape_html, split_message

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

# Per-user локи: load-modify-save без гонок при параллельных сообщениях
_user_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


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


async def send_reply(message: Message, reply: str, model_id: str | None = None) -> None:
    """Отправка ответа: экранируем HTML, режем под лимит Telegram.

    Сырой вывод LLM с ParseMode.HTML без экранирования валит отправку
    (TelegramBadRequest на любом '<'); сообщения >4096 символов Telegram
    не принимает вовсе.
    """
    chunks = split_message(escape_html(reply))
    for i, chunk in enumerate(chunks):
        text = chunk
        if model_id and i == len(chunks) - 1:
            short_model = model_id.split("/")[-1].split(":")[0]
            text += f"\n\n<i>🤖 {short_model}</i>"
        try:
            await message.answer(text)
        except Exception:
            # На всякий случай: фолбэк в plain text
            await message.answer(chunk, parse_mode=None)


# ---------------------------------------------------------------------------
# Core pipeline (общий для текстов и /apply)
# ---------------------------------------------------------------------------
async def process_message(message: Message, user_text: str) -> None:
    user_id = message.from_user.id
    log.info("[%d] → %s", user_id, user_text[:80])

    async with _user_locks[user_id]:
        memory = mem.load(user_id)
        if not memory.profile.user_id:
            memory.profile.user_id = user_id
            memory.profile.name = message.from_user.full_name

        await typing(message.chat.id)

        # Step 0 — ссылка на вакансию? Скрапим, чтобы worker видел реальный текст
        job_context = ""
        urls = extract_urls(user_text)
        if urls:
            job = await scrape_url(urls[0])
            if job and job.description:
                job_context = (
                    f"Title: {job.title}\nSource: {job.source}\nURL: {job.url}\n\n"
                    f"{job.description}"
                )
                log.info("[%d] scraped %s (%d chars)", user_id, urls[0], len(job.description))
            else:
                await message.answer(
                    "⚠️ Не смог открыть ссылку (сайт закрыт от ботов или недоступен).\n"
                    "Скопируй текст вакансии сообщением — тогда отвечу по делу, "
                    "а не по догадкам."
                )

        # Step 1 — ROUTER: категория + извлечение профиля (model_id резолвит сервер)
        decision: RouterDecision = await route(user_text)
        log.info(
            "[%d] router → category=%s model=%s complexity=%d",
            user_id, decision.task_category, decision.model_id, decision.complexity,
        )

        # Step 1.5 — обновление профиля из явных утверждений пользователя
        if decision.profile_updates:
            changed = mem.merge_profile_updates(
                memory, decision.profile_updates.model_dump()
            )
            if changed:
                log.info("[%d] profile updated: %s", user_id, ", ".join(changed))

        await typing(message.chat.id)  # keep typing indicator alive

        # Step 2 — WORKER: основная модель + фолбэк-цепочка
        deps = WorkerDeps(
            user_id=user_id,
            profile=memory.profile,
            conversation_history=memory.conversation_history,
            job_context=job_context,
        )
        reply, used_model = await run_worker(
            model_ids=fallback_models(decision.task_category),
            user_message=user_text,
            deps=deps,
        )

        # Step 3 — Save conversation
        mem.add_message(memory, "user", user_text)
        mem.add_message(memory, "assistant", reply)
        mem.save(memory)

    # Step 4 — Reply (вне лока: отправка не должна держать память)
    await send_reply(message, reply, used_model)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    async with _user_locks[user_id]:
        memory = mem.load(user_id)
        if not memory.profile.name:
            memory.profile.user_id = user_id
            memory.profile.name = message.from_user.full_name
            memory.profile.username = message.from_user.username or ""
            mem.save(memory)

    await message.answer(
        f"👋 Привет, <b>{escape_html(memory.profile.name)}</b>!\n\n"
        "Я помогу найти работу, оценить вакансию и написать резюме.\n\n"
        "<b>Что умею:</b>\n"
        "• Анализировать вакансии по ссылке\n"
        "• Писать CV и cover letter под конкретную вакансию\n"
        "• Отвечать на вопросы о поиске работы\n\n"
        "Просто напиши что тебе нужно, или отправь ссылку на вакансию.\n"
        "Расскажи о себе («Я Python-разработчик, ищу удалёнку») — запомню.\n"
        "Резюме: <code>/cv твой текст резюме</code>\n"
        "Команды: /profile /apply /cv /status /help"
    )


# ---------------------------------------------------------------------------
# /profile
# ---------------------------------------------------------------------------
@dp.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    memory = mem.load(message.from_user.id)
    p = memory.profile

    lines = ["<b>👤 Твой профиль:</b>\n"]
    lines.append(f"Имя: {escape_html(p.name) or '—'}")
    lines.append(f"Профессия: {escape_html(p.profession) or '—'}")
    lines.append(f"Навыки: {escape_html(', '.join(p.skills)) if p.skills else '—'}")
    lines.append(
        f"Локации: {escape_html(', '.join(p.preferred_locations)) if p.preferred_locations else '—'}"
    )
    lines.append(f"Зарплата: {escape_html(p.salary_expectation) or '—'}")
    lines.append(f"Языки: {escape_html(', '.join(p.languages)) if p.languages else '—'}")
    cv_status = f"✅ ({len(p.cv_text)} симв.)" if p.cv_text else "❌ — отправь /cv [текст]"
    lines.append(f"CV загружено: {cv_status}")
    lines.append(
        "\nЧтобы обновить профиль — просто напиши, например:\n"
        "<i>'Я Python разработчик, ищу удалённую работу в Европе'</i>"
    )
    await message.answer("\n".join(lines))


# ---------------------------------------------------------------------------
# /cv — сохранить текст резюме
# ---------------------------------------------------------------------------
@dp.message(Command("cv"))
async def cmd_cv(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or len(args[1].strip()) < 50:
        await message.answer(
            "Отправь резюме одним сообщением:\n"
            "<code>/cv [текст твоего резюме]</code>\n\n"
            "Минимум 50 символов. Я буду использовать его при написании "
            "CV и cover letter."
        )
        return

    user_id = message.from_user.id
    async with _user_locks[user_id]:
        memory = mem.load(user_id)
        if not memory.profile.user_id:
            memory.profile.user_id = user_id
            memory.profile.name = message.from_user.full_name
        memory.profile.cv_text = args[1].strip()
        mem.save(memory)

    await message.answer(
        f"✅ Резюме сохранено ({len(args[1].strip())} символов).\n"
        "Теперь я буду учитывать его при анализе вакансий и написании писем."
    )


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
        "/apply [URL] — резюме и cover letter под вакансию\n"
        "/cv [текст] — сохранить своё резюме\n"
        "/status — статус бота и модели\n"
        "/help — эта справка\n\n"
        "<b>Или просто напиши:</b>\n"
        "• Ссылку на вакансию → скачаю и проанализирую\n"
        "• 'Напиши резюме для...' → готовый текст\n"
        "• 'Я ищу работу в...' → обновлю твой профиль\n"
        "• Любой вопрос о поиске работы"
    )


# ---------------------------------------------------------------------------
# /apply — generate CV + cover letter for a job URL
# ---------------------------------------------------------------------------
@dp.message(Command("apply"))
async def cmd_apply(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not extract_urls(args[1]):
        await message.answer("Укажи URL вакансии: <code>/apply https://...</code>")
        return

    url = extract_urls(args[1])[0]
    try:
        await process_message(
            message,
            f"Напиши резюме и cover letter под эту вакансию: {url}",
        )
    except Exception:
        await _report_error(message, args[1])


# ---------------------------------------------------------------------------
# Main text handler — ROUTER → WORKER pipeline
# ---------------------------------------------------------------------------
@dp.message(F.text)
async def handle_text(message: Message) -> None:
    user_text = message.text or ""

    # Неизвестные команды не отправляем в LLM
    if user_text.startswith("/"):
        await message.answer("Не знаю такую команду. Список: /help")
        return

    try:
        await process_message(message, user_text)
    except Exception:
        await _report_error(message, user_text)


async def _report_error(message: Message, user_text: str) -> None:
    error_text = traceback.format_exc()
    log.error("[%d] error:\n%s", message.from_user.id, error_text)
    await notify_admin(
        f"User {message.from_user.id} (@{message.from_user.username})\n"
        f"Msg: {escape_html(user_text[:100])}\n\n"
        f"<pre>{escape_html(error_text[-1000:])}</pre>"
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
    name = (doc.file_name or "").lower()  # file_name бывает None
    if name and not name.endswith((".pdf", ".docx", ".txt")):
        await message.answer("Поддерживаются форматы: PDF, DOCX, TXT")
        return
    await message.answer(
        f"📄 Получил файл: <b>{escape_html(doc.file_name or 'без имени')}</b>\n\n"
        "Парсинг файлов пока не подключён. Скопируй текст резюме и отправь:\n"
        "<code>/cv [текст резюме]</code>"
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
async def set_commands() -> None:
    await bot.set_my_commands([
        BotCommand(command="start",   description="Начать работу"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="apply",   description="Резюме под вакансию"),
        BotCommand(command="cv",      description="Сохранить резюме"),
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
