---
name: employer-research
version: 1.1.0
description: >
  Use this skill to research a company or employer before applying or interviewing.
  Triggers on any request to evaluate, check, or learn about a company:
  "check the company", "research employer", "what do people say about [company]",
  "is [company] a good place to work", "[company] reviews", "glassdoor [company]",
  "проверь компанию", "оцени работодателя", "отзывы о [company]",
  "стоит ли туда идти", "что за компания", "нормальная ли компания",
  "какой работодатель", "tell me about [company]", "company background",
  "is this company legit", "company culture", "red flags in job posting".
  Also triggers automatically as part of the job-search skill whenever an employer
  card needs to be evaluated for a vacancy.
context: fork
allowed-tools: Browser(*)
---

# Employer Research Skill

**TOTAL TIME LIMIT: 3 minutes maximum.** If you haven't finished in 3 minutes, stop and report what you have.

Research the company using Google search snippets as the PRIMARY method.
Direct site navigation is SECONDARY and only if the first search gives too little.

## Strategy: Search First, Browse Only If Needed

### Step 1: Google search for Glassdoor reviews (30 seconds)

Search for:
```
[company name] glassdoor reviews rating
```

Read the **search result snippets only** — do NOT navigate to glassdoor.com.
Glassdoor blocks bots. The Google snippet usually contains the rating, review count,
and 1-2 sentences about pros/cons. That's enough.

If the snippet has a rating → use it. If not → note "Glassdoor data not in snippet".

### Step 2: Google search for company basics (30 seconds)

Search for:
```
[company name] employees founded headquarters industry
```

From the snippet / knowledge panel extract:
- Employee count
- Founded year
- HQ location
- Industry

### Step 3: Google search for recent news (30 seconds)

Search for:
```
[company name] layoffs OR "mass layoffs" OR funding OR acquisition 2024 OR 2025 OR 2026
```

Read snippets only. Flag anything relevant to job stability.

### Step 4 (OPTIONAL — only if steps 1-3 gave very little): Direct LinkedIn

If after 3 Google searches you have almost no data, try:
```
https://www.linkedin.com/company/[company-slug]/
```
Give it max 20 seconds. If it requires login or doesn't load — skip immediately.

**NEVER navigate to:**
- investor relations pages (investors.spotify.com, ir.company.com, etc.)
- SEC filings or annual reports
- Wikipedia or company's own website (too slow, not relevant for employer quality)
- Any page that requires login

## Output Format

```
🏢 **[Company Name]**
📍 [City, Country] | 👥 [X–Y employees] | 🏥 [Industry] | Founded [year]

⭐ Glassdoor: [X.X]/5 · [N] reviews  [or "Не найдено"]

✅ Плюсы: [2–3 пункта из отзывов]
❌ Минусы: [2–3 пункта]

📰 Новости: [1–2 предложения, или "Ничего нового за 12 месяцев"]
🚦 Красные флаги: [или "Не найдено"]
💡 Вывод: [1–2 честных предложения]
```

## Glassdoor Rating Guide

| Rating | Signal |
|--------|--------|
| 4.0–5.0 | ✅ Хороший работодатель |
| 3.5–3.9 | ⚠️ Смешанно — читай минусы внимательно |
| 3.0–3.4 | ⚠️ Тревожно — называй конкретные проблемы |
| < 3.0 | 🔴 Лучше избегать |
| Нет данных | ❓ Неизвестно — обычно маленькая или новая компания |

## Hard Rules
- **Total time: max 3 minutes.** Stop and report what you have, even if incomplete.
- Never navigate to investor relations, SEC, annual reports, or the company's own website.
- Never spend more than 20 seconds on any single page load.
- If a page is slow or blocked — abort immediately, move to next source.
- Always respond in the same language the user used.
- If data is missing, say so — never fabricate ratings or quotes.
