---
name: employer-research
version: 1.3.0
description: >
  Use this skill to research a company or employer before applying or interviewing.
  Triggers on any request to evaluate, check, or learn about a company:
  "check the company", "research employer", "what do people say about [company]",
  "is [company] a good place to work", "[company] reviews", "glassdoor [company]",
  "проверь компанию", "оцени работодателя", "отзывы о [company]",
  "стоит ли туда идти", "что за компания", "нормальная ли компания",
  "какой работодатель", "tell me about [company]", "company background",
  "is this company legit", "company culture", "red flags in job posting".
context: inline
allowed-tools: Browser(*)
---

# Employer Research Skill

**TOTAL TIME LIMIT: 2 minutes. ONLY use Browser tool. Do NOT use terminal or curl.**

All research is done via Google search URLs in the browser. Read search result snippets only.
Do NOT navigate to Wikipedia, investor relations, SEC, or the company's own website.

## Step 1: Glassdoor rating (30 sec)

Navigate to:
```
https://www.google.com/search?q=[COMPANY]+glassdoor+reviews+rating
```
Read snippets only. Extract: rating (X.X/5), review count, key pros/cons.
Do NOT click any link.

## Step 2: Company basics (30 sec)

Navigate to:
```
https://www.google.com/search?q=[COMPANY]+company+employees+founded+headquarters
```
Extract from Knowledge Panel or snippets: employee count, founded year, HQ, industry.

## Step 3: Recent news (30 sec)

Navigate to:
```
https://www.google.com/search?q=[COMPANY]+layoffs+OR+funding+OR+acquisition+2025+OR+2026
```
Read snippet headlines only. Flag anything affecting job stability.

## Output Format

Deliver immediately after step 3. No more browsing.

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
- Exactly 3 Google searches. Then write the answer immediately.
- Never use terminal or curl.
- Never navigate to Wikipedia, investor relations, or the company's own website.
- 15 second max per page load. If slow — skip and move on.
- Always respond in the user's language.
