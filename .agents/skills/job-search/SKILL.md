---
name: job-search
version: 1.1.0
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
context: inline
allowed-tools: Bash(python3 /root/.hermes/profiles/jabba/skills/job-search/search.py *), Browser(*)
---

# Job Search Skill

**IMPORTANT: To search for jobs, ALWAYS use the script below. Do NOT browse job sites manually. Do NOT use curl.**

Search script: `python3 /root/.hermes/profiles/jabba/skills/job-search/search.py`

This script queries JSearch API (aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter) and returns structured JSON.

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
  --days 30 \
  --max 10
```

For remote jobs use `--remote` flag instead of `--location`.

Example commands:
```bash
# Remote Python developer jobs
python3 /root/.hermes/profiles/jabba/skills/job-search/search.py --query "Python developer" --remote --days 30 --max 10

# Senior backend engineer in UK
python3 /root/.hermes/profiles/jabba/skills/job-search/search.py --query "senior backend engineer" --location "United Kingdom" --days 30 --max 10

# Data analyst in Germany
python3 /root/.hermes/profiles/jabba/skills/job-search/search.py --query "data analyst" --location "Germany" --days 30 --max 10
```

If the script returns `"error": "JSEARCH_API_KEY not set"`, tell the user to add the key to `/root/.hermes/profiles/jabba/.env`.

If first search returns 0 results, try a broader query (e.g. remove location, or simplify role).

## Step 3: Research Each Employer on Glassdoor

For every job you plan to present, use the browser to search:
```
https://www.google.com/search?q=[company name]+glassdoor+reviews+rating
```
Read the search result snippets only — do NOT navigate to glassdoor.com directly.
Extract: rating, review count, key pros/cons from snippets.

## Step 4: Assess Fit %

For each vacancy, compare requirements to the user's profile in memory:
- ✓ matching skills / experience → count them
- ✗ gaps → count and flag if critical
- Fit % = (matched / total key requirements) × 100

## Step 5: Segment, Then Present

### Segment first
Group jobs into 2-4 logical buckets. Present segment names + 1-line description. Ask user to rank by interest. Then show vacancies from preferred segments.

### Per-vacancy card:
```
**[Job Title]** — [Company Name]
📍 [Location] · [🏠 Remote / 🏢 On-site] | 💰 [Salary or "Not listed"] | 📅 [X days ago]
🎯 Fit: [X]% | ⭐ Glassdoor: [rating]/5

✅ Match: [key matching skills]
❌ Gaps: [missing]
🏢 Employer: [1-2 sentences]

🔗 [Apply](URL)
```

## Hard Rules
- **ALWAYS use the search.py script. Never browse job sites manually.**
- Never present a vacancy without employer check
- Max 5 vacancies per message
- Always respond in the same language the user used
- Never search Russian job sites
