---
name: employer-research
version: 1.0.0
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

Research a company using Glassdoor, LinkedIn, and web search via the Camofox browser.
Goal: give the user a clear, honest employer card in under 2 minutes.

## What to Research

For each company, collect:
1. **Glassdoor data** — rating, review count, sentiment patterns, red flags
2. **LinkedIn data** — company size, industry, founding year, recent activity
3. **News check** — any recent layoffs, controversies, funding, acquisitions

## Step 1: Glassdoor

Navigate to:
```
https://www.glassdoor.com/Search/results.htm?keyword=[company name]
```

If Glassdoor loads a company page, extract:
- Overall rating (X.X / 5)
- Total number of reviews
- CEO approval % (if shown)
- “Recommend to a friend” % (if shown)
- Top 3–5 **most recent** reviews: note recurring themes
  - positive: what employees consistently praise
  - negative: what employees consistently criticize
- “Cons” keywords to flag: "micromanagement", "toxic", "no work-life balance",
  "high turnover", "mass layoffs", "promises not kept", "no growth"

If Glassdoor is blocked or slow (>15s to load), try:
```
[company name] site:glassdoor.com reviews
```
via web search, then extract from the search snippet.

If nothing found on Glassdoor, note: “Not on Glassdoor — too small or too new.”

## Step 2: LinkedIn

Navigate to:
```
https://www.linkedin.com/company/[company-name-slug]/
```
(Replace spaces with hyphens, all lowercase.)

Extract:
- Company size (employee count range)
- Industry / sector
- Headquarters location
- Founded year
- Follower count (rough proxy for visibility)
- Any recent posts or announcements (hiring spree? layoffs announced?)

If LinkedIn blocks or requires login:
```
[company name] linkedin company size employees founded
```
Search this via browser and extract from Google snippet.

## Step 3: News Check

Search:
```
[company name] layoffs OR scandal OR funding OR acquisition 2024 OR 2025
```

Scan top 3–5 results. Flag anything in the last 12 months that affects job security:
- Mass layoffs → ⚠️ high risk
- Financial trouble / bankruptcy proceedings → ⚠️
- Acquisition / merger → ⚠️ (role stability uncertain)
- Fresh funding round → ✅ (growth mode, likely hiring)
- IPO → neutral, note it

## Output Format

Present as a compact employer card:

```
🏢 **[Company Name]**
📍 [City, Country] | 👥 [X–Y employees] | 🏥 [Industry] | Founded [year]

⭐ Glassdoor: [X.X]/5 · [N] reviews | CEO approval: [X%] | Recommend: [X%]

✅ **Pros:** [2–3 recurring positives from reviews]
❌ **Cons:** [2–3 recurring negatives]

📰 **Recent news:** [1–2 sentence summary, or "Nothing notable in last 12 months"]

🚦 **Red flags:** [list any, or "None found"]

💡 **Verdict:** [1–2 sentence honest summary — is it worth applying?]
```

## Scoring Guidelines

| Glassdoor | Signal |
|-----------|--------|
| 4.0–5.0 | ✅ Strong employer |
| 3.5–3.9 | ⚠️ Mixed — read cons carefully |
| 3.0–3.4 | ⚠️ Concerning — flag specific issues |
| < 3.0 | 🔴 Avoid unless user has strong reason |
| No data | ❓ Unknown — proceed with caution |

## Hard Rules
- Never fabricate ratings or quotes — if you couldn’t load the page, say so
- Never skip the news check for companies with < 3.5 Glassdoor or < 100 reviews
- Always respond in the same language the user used
- If the company is a staffing agency / recruiter (not the actual employer), note it and try to research the end client if named
- Time limit: complete the full card in under 3 minutes of browsing
