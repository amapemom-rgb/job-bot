---
name: job-search
version: 1.0.0
description: >
  Use this skill to search for job vacancies, openings, and career opportunities.
  Triggers on any job search request: "find jobs", "search vacancies", "look for work",
  "job openings", "найди работу", "ищи вакансии", "поиск работы", "найди вакансию",
  "работа в [country/city]", "remote jobs", "вакансии [role]", "job in [city]",
  "positions for [role]", "hiring [role]", "I'm looking for a job",
  "хочу найти работу", "есть ли вакансии", "покажи вакансии", "что есть на рынке",
  "обнови вакансии", "новые вакансии", "дайджест вакансий".
  Covers: USA, Canada, UK, Europe (Germany, Netherlands, France, Spain, Italy, etc.),
  Australia, Japan. Handles all employment types: full-time, part-time, contract,
  remote, hybrid. Does NOT cover Russian job sites (hh.ru, superjob, etc.).
context: fork
allowed-tools: Bash(python3 /root/.hermes/profiles/jabba/skills/job-search/search.py *), Browser(*)
---

# Job Search Skill

Search for job listings via JSearch API (aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter)
and enrich each result with Glassdoor employer research.

## Before You Start

Check memory for the user's profile: role, skills, experience level, preferred countries,
employment type, salary expectations. Use whatever is already known — never ask for info
you already have. Only ask for what's genuinely missing (max 2 questions at once).

## Step 1: Build the Search Query

From the user's message and profile, extract:
- **role**: job title or skills (e.g. "Backend Developer", "Data Analyst", "Product Manager")
- **location**: specific city, country, region, or "remote"
- **recency**: default last 30 days; use 7 days if user wants fresh postings
- **max results**: default 10

## Step 2: Run the Search Script

```bash
python3 /root/.hermes/profiles/jabba/skills/job-search/search.py \
  --query "[role + 1-2 key skills]" \
  --location "[city or country]" \
  --days [7 or 30] \
  --max 10
```

For remote jobs: use `--remote` flag instead of `--location`.

If the script returns `JSEARCH_API_KEY not set`, tell the user:
> "Нужен бесплатный ключ JSearch (500 запросов/мес). Зарегистрируйся на https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch и добавь JSEARCH_API_KEY в /root/.hermes/profiles/jabba/.env"

If first search returns fewer than 5 results, run a second search with a broader query variation.

## Step 3: Research Each Employer on Glassdoor

For every job you plan to present, use the browser:
1. Go to: `https://www.glassdoor.com/Search/results.htm?keyword=[company name]`
2. Extract: overall rating (X/5), total reviews, CEO Approval %, "Recommend to Friend" %
3. Scan top 3-5 reviews for recurring themes
4. Note red flags: mass layoffs, "toxic management", unexplained turnover, sudden culture shift

Time limit: max ~30 seconds per company. If Glassdoor blocks, try:
`[company name] glassdoor reviews` via web search.

If you find nothing — say so honestly, don't fabricate.

## Step 4: Assess Fit %

For each vacancy, compare requirements to the user's profile in memory:
- ✓ matching skills / experience → count them
- ✗ gaps → count and flag if critical
- Fit % = (matched / total key requirements) × 100

If the profile is incomplete for accurate scoring, use a rough estimate and add `(~approx)`.
Fit < 40% → label as "Stretch role".

## Step 5: Segment, Then Present

### Segment first
Group jobs into 2-4 logical buckets based on what you see:
examples: "startup vs. enterprise", "remote vs. office", "senior vs. mid-level",
"product company vs. consulting", "German market vs. US remote".

Present segment names + 1-line description each. Ask user to rank by interest.
Then show vacancies from their preferred segments.

### Per-vacancy card:
```
**[Job Title]** — [Company Name]
📍 [City, Country] · [🏠 Remote / 🏢 On-site / 🔀 Hybrid] | 💰 [Salary or "Not listed"] | 📅 [X days ago]
🎯 Fit: [X]% | ⭐ Glassdoor: [rating]/5 ([N] reviews) [or "Not found"]

✅ Match: [key matching skills]
❌ Gaps: [missing — mark critical ones with ⚠️]
📋 Ad quality: [direct/recruiter post · salary listed Y/N · description detail: high/med/low]
🏢 Employer: [1-2 sentences. Red flags → ⚠️]

🔗 [Apply](URL)
```

## Hard Rules
- Never present a vacancy without completing the employer check
- Flag postings older than 30 days with ⚠️ (likely already closed)
- Max 5 vacancies per message; offer "Показать ещё?" after
- "Not listed" for salary — never skip or assume
- Always respond in the same language the user used in their message
- Never search Russian job sites (hh.ru, superjob, rabota.ru, etc.)
