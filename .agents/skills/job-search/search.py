#!/usr/bin/env python3
"""
JSearch API client for Jabba job search bot.
Aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter results.

Usage:
  python3 search.py --query "software engineer" --location "Germany" --days 30 --max 10
  python3 search.py --query "data analyst" --remote --days 7

Requires: JSEARCH_API_KEY env var (free at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests not installed. Run: pip3 install requests"}))
    sys.exit(1)


def search_jobs(
    query: str,
    location: str = None,
    remote: bool = False,
    days_posted: int = 30,
    max_results: int = 10,
) -> dict:
    api_key = os.environ.get("JSEARCH_API_KEY")
    if not api_key:
        return {
            "error": (
                "JSEARCH_API_KEY not set. "
                "Get a free key (500 req/month) at: "
                "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch "
                "then add JSEARCH_API_KEY=your_key to /root/.hermes/profiles/jabba/.env"
            )
        }

    # Build natural-language query for JSearch
    if remote:
        search_query = f"{query} remote"
    elif location:
        search_query = f"{query} in {location}"
    else:
        search_query = query

    date_map = {1: "today", 3: "3days", 7: "week", 30: "month"}
    date_posted = date_map.get(days_posted, "month")

    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    params = {
        "query": search_query,
        "page": "1",
        "num_pages": "2",  # 2 pages = up to 20 raw results
        "date_posted": date_posted,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return {"error": "JSearch API timeout (>20s). Try again later."}
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            return {"error": "JSearch API rate limit reached (500 req/month). Try tomorrow."}
        return {"error": f"HTTP error {response.status_code}: {str(e)}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

    if data.get("status") != "OK":
        return {"error": f"API error: {data.get('message', 'Unknown')}"}

    jobs = []
    for job in data.get("data", [])[:max_results]:
        # Parse posting date
        days_ago = None
        posted_raw = job.get("job_posted_at_datetime_utc", "")
        if posted_raw:
            try:
                posted_dt = datetime.fromisoformat(posted_raw.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - posted_dt).days
            except Exception:
                pass

        # Salary
        salary_min = job.get("job_min_salary")
        salary_max = job.get("job_max_salary")
        salary_period = job.get("job_salary_period", "year") or "year"
        salary_currency = job.get("job_salary_currency", "USD") or "USD"

        if salary_min and salary_max:
            salary = f"{salary_currency} {int(salary_min):,}–{int(salary_max):,}/{salary_period}"
        elif salary_min:
            salary = f"{salary_currency} {int(salary_min):,}+/{salary_period}"
        else:
            salary = None

        # Location string
        city = job.get("job_city") or ""
        state = job.get("job_state") or ""
        country = job.get("job_country") or ""
        location_parts = [p for p in [city, state, country] if p]
        location_str = ", ".join(location_parts) if location_parts else "Not specified"

        # Required skills (top 8 to keep it readable)
        required_skills = (job.get("job_required_skills") or [])[:8]

        # Job highlights (bullets from description)
        highlights = job.get("job_highlights") or {}
        qualifications = (highlights.get("Qualifications") or [])[:5]
        responsibilities = (highlights.get("Responsibilities") or [])[:3]

        jobs.append({
            "title": job.get("job_title", ""),
            "company": job.get("employer_name", ""),
            "location": location_str,
            "is_remote": job.get("job_is_remote", False),
            "employment_type": job.get("job_employment_type", ""),
            "salary": salary,
            "posted_days_ago": days_ago,
            "source": job.get("job_publisher", ""),
            "required_skills": required_skills,
            "qualifications": qualifications,
            "responsibilities": responsibilities,
            "description_preview": (job.get("job_description") or "")[:600].strip(),
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
        "query": search_query,
        "total_found": data.get("data_count", len(jobs)),
        "returned": len(jobs),
        "jobs": jobs,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search jobs via JSearch API (LinkedIn/Indeed/Glassdoor aggregator)"
    )
    parser.add_argument("--query", required=True, help="Job title or skills")
    parser.add_argument("--location", help="City, country, or region (omit for --remote)")
    parser.add_argument("--remote", action="store_true", help="Search for remote jobs")
    parser.add_argument(
        "--days", type=int, default=30, choices=[1, 3, 7, 30],
        help="Posted within N days (default: 30)"
    )
    parser.add_argument(
        "--max", type=int, default=10,
        help="Max results to return (default: 10)"
    )

    args = parser.parse_args()

    result = search_jobs(
        query=args.query,
        location=args.location,
        remote=args.remote,
        days_posted=args.days,
        max_results=args.max,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
