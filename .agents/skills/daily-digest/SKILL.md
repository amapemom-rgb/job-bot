---
name: daily-digest
version: 1.0.0
description: >
  Use this skill to send the user a daily summary of new job vacancies.
  Triggers on scheduled daily digest run, or when user asks for:
  "дайджест вакансий", "новые вакансии за сегодня", "что появилось нового",
  "daily digest", "what's new today", "new jobs today", "show me today's jobs",
  "есть новые вакансии", "что на рынке сегодня", "обновления",
  "morning briefing", "утренная подборка".
context: fork
allowed-tools: Bash(python3 /root/.hermes/profiles/jabba/skills/job-search/search.py *), Bash(python3 /root/.hermes/profiles/jabba/skills/daily-digest/tracker.py *), Browser(*)
---

# Daily Digest Skill

Search for jobs posted in the last 24 hours, filter out already-seen ones,
and send a concise digest. Only NEW vacancies — never repeat what the user already saw.

## Step 1: Load User Profile

From memory, retrieve:
- Target roles (e.g. "Python developer", "Data Engineer")
- Target countries / cities
- Employment preferences (remote / hybrid / on-site)
- Any roles or companies the user explicitly said to skip

If no search criteria are saved yet, tell the user:
> "Прежде чем запустить дайджест, мне нужно знать: какую роль ищем, в каких странах и формат работы?"

## Step 2: Search for Today's Jobs

Run the search script with `--days 1` for each saved search profile:

```bash
python3 /root/.hermes/profiles/jabba/skills/job-search/search.py \
  --query "[role]" \
  --location "[location]" \
  --days 1 \
  --max 15
```

If the user has multiple roles or locations, run separate queries and merge results.

## Step 3: Filter Already-Seen Jobs

Check which jobs were already shown to the user:

```bash
# Check a list of apply_urls against seen history
python3 /root/.hermes/profiles/jabba/skills/daily-digest/tracker.py check \
  --urls "[url1]" "[url2]" ...
```

Only keep jobs whose URL is NOT in the seen list.

Then mark the new jobs as seen:
```bash
python3 /root/.hermes/profiles/jabba/skills/daily-digest/tracker.py mark \
  --urls "[url1]" "[url2]" ...
```

## Step 4: Quick Employer Check

For each new job, do a fast Glassdoor check (same as employer-research skill).
Time limit: 20 seconds per company. For the digest, use a shorter format.

## Step 5: Send Digest

### If 0 new jobs found:
```
📬 Дайджест [date]
Новых вакансий сегодня нет. Вернусь завтра.
```

### If new jobs found, send compact digest (max 5 per digest):
```
📬 Дайджест [date] — [N] новых вакансий

1️⃣ **[Job Title]** — [Company]
   📍 [Location] | 💰 [Salary / Not listed] | ⭐ [X.X]/5
   🎯 Fit: [X]% | 🔗 [Apply](URL)

2️⃣ ...

—
🔍 Показать подробности по любой? Отвечу номером.
```

If there are more than 5 new jobs, add at the end:
```
Ещё [N-5] вакансий — напиши «ещё» чтобы увидеть.
```

## Hard Rules
- Only show jobs posted in the last 24 hours
- Never repeat a vacancy the user has already seen
- Skip companies the user explicitly rejected
- Max 5 per digest message
- Respond in the user's language
- If JSearch API key is not set, notify the user once and stop
