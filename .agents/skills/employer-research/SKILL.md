---
name: employer-research
version: 1.2.0
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

**TOTAL TIME LIMIT: 2 minutes.** Use ONLY the Browser tool. Do NOT use terminal, curl, or any other tool.

All research is done by navigating to Google search URLs in the browser and reading the results page.
Do NOT navigate to Wikipedia, investor relations, SEC filings, or the company's own website.

## Step 1: Glassdoor rating via Google (30 sec)

Navigate to this exact URL (replace COMPANY with the actual company name, URL-encoded):
```
https://www.google.com/search?q=COMPANY+glassdoor+reviews+rating
```
Example for Stripe: `https://www.google.com/search?q=Stripe+glassdoor+reviews+rating`

Read the search results page. Look for:
- A rating snippet (e.g. "4.1 stars · 3,200 reviews")
- Short text about pros/cons from the Glassdoor listing in the snippet

Do NOT click any link. Read only what's on the search results page.

## Step 2: Company basics via Google (30 sec)

Navigate to:
```
https://www.google.com/search?q=COMPANY+company+employees+founded+headquarters
```

Read the Knowledge Panel on the right side of results (if present) or the snippets.
Extract: employee count, founded year, HQ, industry.

## Step 3: Recent news via Google (30 sec)

Navigate to:
```
https://www.google.com/search?q=COMPANY+layoffs+OR+funding+OR+acquisition+2025+OR+2026
```

Read snippet headlines only. Flag anything affecting job stability.

## Output Format

Deliver the result immediately after step 3. Do not do any more browsing.

```
🏢 **[Company Name]**
📍 [City, Country] | 👥 [employees] | 🏥 [Industry] | Founded [year]

⭐ Glassdoor: [X.X]/5 · [N отзывов]  [или "Не найдено"]

✅ Плюсы: ...
❌ Минусы: ...

📰 Новости: ...
🚦 Красные флаги: [или "Не найдено"]
💡 Вывод: ...
```

## Hard Rules
- Use ONLY browser_navigate. Never use terminal or curl.
- Never navigate to: Wikipedia, investor relations, SEC, annual reports, company's own site.
- If a page takes more than 15 seconds to load — stop and move to the next step.
- Exactly 3 browser navigations total (one per step). Then write the answer.
- Always respond in the same language the user used.
- If data is missing, say so honestly — never fabricate.
