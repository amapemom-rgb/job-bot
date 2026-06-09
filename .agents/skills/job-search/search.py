#!/usr/bin/env python3
"""
Jabba job search aggregator.
Sources (in priority order):
  1. Himalayas API  — 104K+ remote jobs, free, no key needed
  2. JSearch API    — LinkedIn/Indeed/Glassdoor, requires JSEARCH_API_KEY
  3. Remotive API   — ~17-30 remote jobs, free, no key needed

Usage:
  python3 search.py --query "Python developer" --remote --days 30 --max 10
  python3 search.py --query "backend engineer" --location "Germany" --days 30 --max 10
  python3 search.py --query "data analyst" --remote --days 7 --max 5 --source himalayas
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests not installed. Run: pip3 install requests"}))
    sys.exit(1)

# ── Load .env if API key not in environment ───────────────────────────────────
_env_file = Path("/root/.hermes/profiles/jabba/.env")
if not os.environ.get("JSEARCH_API_KEY") and _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            if _line.startswith("JSEARCH_API_KEY="):
                os.environ["JSEARCH_API_KEY"] = _line.strip().split("=", 1)[1]
                break


# ── Himalayas API ─────────────────────────────────────────────────────────────
def search_himalayas(
    query: str,
    location: str = None,
    remote: bool = False,
    days_posted: int = 30,
    max_results: int = 10,
) -> dict:
    """
    Himalayas.app public API — 104K+ remote jobs, no API key required.
    Server-side filters are unreliable, so we filter locally.
    """
    url = "https://himalayas.app/jobs/api"
    # Fetch a larger batch to filter from (server filters don’t work well)
    params = {"limit": 200, "offset": 0}

    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"error": "Himalayas API timeout"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Himalayas request failed: {e}"}

    jobs_raw = data.get("jobs", [])
    if not jobs_raw:
        return {"error": "Himalayas returned no jobs"}

    # Local filtering
    query_words = [w.lower() for w in query.split()]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_posted)

    jobs = []
    for job in jobs_raw:
        # Match query against title + categories
        title = (job.get("title") or "").lower()
        cats = " ".join(job.get("categories") or []).lower()
        desc_preview = (job.get("description") or "")[:200].lower()
        text = f"{title} {cats} {desc_preview}"

        if not any(w in text for w in query_words):
            continue

        # Location filter
        loc_restrictions = job.get("locationRestrictions") or []
        if location and not remote:
            loc_str = " ".join(loc_restrictions).lower()
            if location.lower() not in loc_str and "worldwide" not in loc_str:
                continue

        # Date filter
        posted_raw = job.get("createdAt") or job.get("publishedAt") or ""
        days_ago = None
        if posted_raw:
            try:
                posted_dt = datetime.fromisoformat(posted_raw.replace("Z", "+00:00"))
                if posted_dt < cutoff:
                    continue
                days_ago = (datetime.now(timezone.utc) - posted_dt).days
            except Exception:
                pass

        # Salary
        sal_min = job.get("minSalary")
        sal_max = job.get("maxSalary")
        currency = job.get("currency") or "USD"
        if sal_min and sal_max:
            salary = f"{currency} {int(sal_min):,}–{int(sal_max):,}/year"
        elif sal_min:
            salary = f"{currency} {int(sal_min):,}+/year"
        else:
            salary = None

        jobs.append({
            "title": job.get("title", ""),
            "company": job.get("companyName") or job.get("company", {}).get("name", ""),
            "location": ", ".join(loc_restrictions) if loc_restrictions else "Remote",
            "is_remote": True,
            "employment_type": job.get("employmentType", ""),
            "seniority": job.get("seniority") or job.get("jobLevel", ""),
            "salary": salary,
            "posted_days_ago": days_ago,
            "source": "Himalayas",
            "required_skills": (job.get("categories") or [])[:6],
            "qualifications": [],
            "responsibilities": [],
            "description_preview": (job.get("description") or "")[:500].strip(),
            "apply_url": job.get("applicationUrl") or job.get("url") or "",
            "experience_required": {"months": None, "no_experience_required": False},
            "education_required": {"level": "", "no_degree": False},
        })

        if len(jobs) >= max_results:
            break

    return {
        "source": "himalayas",
        "query": query,
        "total_found": len(jobs),
        "returned": len(jobs),
        "jobs": jobs,
    }


# ── Remotive API ──────────────────────────────────────────────────────────────
def search_remotive(query: str, max_results: int = 10) -> dict:
    """Remotive public API — ~17-30 remote tech jobs, no API key required."""
    url = "https://remotive.com/api/remote-jobs"
    params = {"category": "software-dev", "limit": 50}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Remotive request failed: {e}"}

    query_words = [w.lower() for w in query.split()]
    jobs = []
    for job in data.get("jobs", []):
        text = f"{job.get('title', '')} {' '.join(job.get('tags', []))}".lower()
        if not any(w in text for w in query_words):
            continue

        # Parse date
        days_ago = None
        pub_date = job.get("publication_date", "")
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - dt).days
            except Exception:
                pass

        jobs.append({
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": job.get("candidate_required_location") or "Remote",
            "is_remote": True,
            "employment_type": job.get("job_type", ""),
            "seniority": "",
            "salary": job.get("salary") or None,
            "posted_days_ago": days_ago,
            "source": "Remotive",
            "required_skills": (job.get("tags") or [])[:6],
            "qualifications": [],
            "responsibilities": [],
            "description_preview": "",
            "apply_url": job.get("url", ""),
            "experience_required": {"months": None, "no_experience_required": False},
            "education_required": {"level": "", "no_degree": False},
        })

        if len(jobs) >= max_results:
            break

    return {
        "source": "remotive",
        "query": query,
        "total_found": len(jobs),
        "returned": len(jobs),
        "jobs": jobs,
    }


# ── JSearch API ───────────────────────────────────────────────────────────────
def search_jsearch(
    query: str,
    location: str = None,
    remote: bool = False,
    days_posted: int = 30,
    max_results: int = 10,
) -> dict:
    """JSearch via RapidAPI — aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter."""
    api_key = os.environ.get("JSEARCH_API_KEY")
    if not api_key:
        return {"error": "JSEARCH_API_KEY not set. Get free key at rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"}

    search_query = f"{query} remote" if remote else (f"{query} in {location}" if location else query)
    date_map = {1: "today", 3: "3days", 7: "week", 30: "month"}

    try:
        resp = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"},
            params={"query": search_query, "page": "1", "num_pages": "2",
                    "date_posted": date_map.get(days_posted, "month")},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"error": "JSearch API timeout"}
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 429:
            return {"error": "JSearch rate limit (500 req/month). Try tomorrow."}
        return {"error": f"JSearch HTTP {resp.status_code}: {e}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"JSearch request failed: {e}"}

    if data.get("status") != "OK":
        return {"error": f"JSearch error: {data.get('message', 'Unknown')}"}

    jobs = []
    for job in data.get("data", [])[:max_results]:
        days_ago = None
        posted_raw = job.get("job_posted_at_datetime_utc", "")
        if posted_raw:
            try:
                dt = datetime.fromisoformat(posted_raw.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - dt).days
            except Exception:
                pass

        sal_min = job.get("job_min_salary")
        sal_max = job.get("job_max_salary")
        sal_cur = job.get("job_salary_currency", "USD") or "USD"
        sal_per = job.get("job_salary_period", "year") or "year"
        if sal_min and sal_max:
            salary = f"{sal_cur} {int(sal_min):,}–{int(sal_max):,}/{sal_per}"
        elif sal_min:
            salary = f"{sal_cur} {int(sal_min):,}+/{sal_per}"
        else:
            salary = None

        city = job.get("job_city") or ""
        country = job.get("job_country") or ""
        location_str = ", ".join(p for p in [city, country] if p) or "Not specified"

        jobs.append({
            "title": job.get("job_title", ""),
            "company": job.get("employer_name", ""),
            "location": location_str,
            "is_remote": job.get("job_is_remote", False),
            "employment_type": job.get("job_employment_type", ""),
            "seniority": "",
            "salary": salary,
            "posted_days_ago": days_ago,
            "source": job.get("job_publisher", "JSearch"),
            "required_skills": (job.get("job_required_skills") or [])[:6],
            "qualifications": ((job.get("job_highlights") or {}).get("Qualifications") or [])[:4],
            "responsibilities": ((job.get("job_highlights") or {}).get("Responsibilities") or [])[:3],
            "description_preview": (job.get("job_description") or "")[:500].strip(),
            "apply_url": job.get("job_apply_link", ""),
            "experience_required": {
                "months": (job.get("job_required_experience") or {}).get("required_experience_in_months"),
                "no_experience_required": (job.get("job_required_experience") or {}).get("no_experience_required", False),
            },
            "education_required": {
                "level": (job.get("job_required_education") or {}).get("required_education_level", ""),
                "no_degree": (job.get("job_required_education") or {}).get("no_degree_required", False),
            },
        })

    return {
        "source": "jsearch",
        "query": search_query,
        "total_found": data.get("data_count", len(jobs)),
        "returned": len(jobs),
        "jobs": jobs,
    }


# ── Main aggregator ───────────────────────────────────────────────────────────
def search_jobs(
    query: str,
    location: str = None,
    remote: bool = False,
    days_posted: int = 30,
    max_results: int = 10,
    source: str = "auto",
) -> dict:
    """
    Aggregate results from multiple sources.
    source: "auto" | "himalayas" | "jsearch" | "remotive" | "all"
    """
    results = []
    errors = []

    if source in ("auto", "all", "himalayas"):
        r = search_himalayas(query, location, remote, days_posted, max_results)
        if "error" in r:
            errors.append(f"Himalayas: {r['error']}")
        else:
            results.extend(r["jobs"])

    if source in ("all", "jsearch") or (source == "auto" and len(results) < 5):
        r = search_jsearch(query, location, remote, days_posted, max_results)
        if "error" in r:
            errors.append(f"JSearch: {r['error']}")
        else:
            # Avoid duplicates by title+company
            seen = {(j["title"].lower(), j["company"].lower()) for j in results}
            for j in r["jobs"]:
                key = (j["title"].lower(), j["company"].lower())
                if key not in seen:
                    results.append(j)
                    seen.add(key)

    if source in ("all", "remotive") or (source == "auto" and len(results) < 5):
        r = search_remotive(query, max_results)
        if "error" in r:
            errors.append(f"Remotive: {r['error']}")
        else:
            seen = {(j["title"].lower(), j["company"].lower()) for j in results}
            for j in r["jobs"]:
                key = (j["title"].lower(), j["company"].lower())
                if key not in seen:
                    results.append(j)
                    seen.add(key)

    results = results[:max_results]

    return {
        "query": query,
        "sources_used": list({j["source"] for j in results}),
        "sources_errors": errors if errors else None,
        "total_found": len(results),
        "returned": len(results),
        "jobs": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Jabba job search aggregator")
    parser.add_argument("--query", required=True, help="Job title or skills")
    parser.add_argument("--location", help="City or country (omit for --remote)")
    parser.add_argument("--remote", action="store_true", help="Remote jobs only")
    parser.add_argument("--days", type=int, default=30, choices=[1, 3, 7, 30],
                        help="Posted within N days (default: 30)")
    parser.add_argument("--max", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--source", default="auto",
                        choices=["auto", "himalayas", "jsearch", "remotive", "all"],
                        help="Data source (default: auto)")
    args = parser.parse_args()

    result = search_jobs(
        query=args.query,
        location=args.location,
        remote=args.remote,
        days_posted=args.days,
        max_results=args.max,
        source=args.source,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
