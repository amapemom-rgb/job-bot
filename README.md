# job-bot

AI-powered job search Telegram bot.

**Stack:** Pydantic AI · aiogram 3 · OpenRouter (multiple free LLMs)

## Architecture

```
User (Telegram)
    │
    ▼
  bot.py          ← aiogram handler
    │
    ▼
ROUTER agent      ← cheap free model decides which model to use
    │
    ▼
WORKER agent      ← the right model executes the task
    │
    ▼
  reply to user
```

## Smart Model Routing

| Task | Model | Cost |
|---|---|---|
| Routing | `google/gemma-4-26b-a4b-it:free` | $0 |
| Chat / simple | `google/gemma-4-26b-a4b-it:free` | $0 |
| Job evaluation | `nvidia/nemotron-3-super-120b-a12b:free` | $0 |
| CV / cover letter | `nvidia/nemotron-3-ultra-550b-a55b:free` | $0 |
| Code / technical | `qwen/qwen3-coder:free` | $0 |
| Critical (fallback) | `anthropic/claude-sonnet-4-5` | ~$3/M |

## Setup

```bash
# 1. Clone
git clone https://github.com/amapemom-rgb/job-bot.git
cd job-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your keys

# 4. Run
python bot.py
```

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome + setup profile |
| `/profile` | View / update your profile |
| `/apply [url]` | Generate CV + cover letter for job |
| `/status` | Bot status and active model info |
| `/help` | Show all commands |

## Project Structure

```
job-bot/
├── bot.py                  # Telegram entry point
├── config.py               # Models + settings
├── agents/
│   ├── router_agent.py     # ROUTER — decides which model
│   └── worker_agent.py     # WORKER — executes the task
├── memory/
│   └── user_memory.py      # User profile + history
├── jobs/
│   └── scraper.py          # Job portal scraping
├── data/                   # User data (gitignored)
├── requirements.txt
└── .env.example
```

## Based on
[ai-job-search](https://github.com/MadsLorentzen/ai-job-search) by MadsLorentzen (MIT License)
