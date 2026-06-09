---
name: daily-digest
version: 1.1.0
description: >
  Use this skill to send the user a daily summary of new job vacancies.
  Triggers on scheduled daily digest run, or when user asks for:
  "дайджест вакансий", "новые вакансии за сегодня", "что появилось нового",
  "daily digest", "what's new today", "new jobs today", "show me today's jobs",
  "есть новые вакансии", "что на рынке сегодня", "обновления",
  "morning briefing", "утренная подборка".
context: inline
allowed-tools: Bash(python3 /root/.hermes/profiles/jabba/skills/job-search/search.py *), Bash(python3 /root/.hermes/profiles/jabba/skills/daily-digest/tracker.py *), Browser(*)
---

# Daily Digest Skill

Search for jobs posted in the last 24 hours, filter out already-seen ones, send compact digest.

**ALWAYS use the search.py script. Never browse job sites manually.**

## Step 1: Load User Profile

From memory: target roles, countries, employment preferences, companies to skip.
If no criteria saved, ask user before proceeding.

## Step 2: Search for Today's Jobs

```bash
python3 /root/.hermes/profiles/jabba/skills/job-search/search.py \
  --query "[role]" \
  --[location "[location]" | --remote] \
  --days 1 \
  --max 15
```

Run separate queries for each saved role/location combo.

## Step 3: Filter Already-Seen Jobs

```bash
# Check which URLs are new
python3 /root/.hermes/profiles/jabba/skills/daily-digest/tracker.py check \
  --urls "[url1]" "[url2]" ...

# Mark them as seen
python3 /root/.hermes/profiles/jabba/skills/daily-digest/tracker.py mark \
  --urls "[url1]" "[url2]" ...
```

## Step 4: Quick Employer Check

For each new job, run one Google search for Glassdoor rating (max 20 sec per company).

## Step 5: Send Digest

### If 0 new jobs:
```
📬 Дайджест [date] — новых вакансий нет. Вернусь завтра.
```

### If new jobs found (max 5):
```
📬 Дайджест [date] — [N] новых вакансий

1️⃣ **[Title]** — [Company]
   📍 [Location] | 💰 [Salary / Not listed] | ⭐ [X.X]/5
   🎯 Fit: [X]% | 🔗 [Apply](URL)
...

🔍 Подробности по любой? Отвечу номером.
```

## Hard Rules
- ALWAYS use search.py script
- Never repeat seen vacancies
- Max 5 per digest
- Respond in user's language
