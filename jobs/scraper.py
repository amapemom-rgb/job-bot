"""Job scraping utilities.

Based on: https://github.com/MadsLorentzen/ai-job-search (MIT)

Currently:
- scrape_url() — extracts text from any job posting URL
- search_jobs() — placeholder (wire up real portals here)

To add a new portal: implement async def search_<portal>(query, location, limit) -> list[Job]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    salary: str = ""
    posted_at: str = ""
    source: str = ""


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


async def scrape_url(url: str) -> Optional[Job]:
    """Scrape a single job posting and return a Job with description text."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title = (
            (soup.find("h1") and soup.find("h1").get_text(strip=True))
            or (soup.find("title") and soup.find("title").get_text(strip=True))
            or "Unknown position"
        )

        # Clean + extract main text
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        description = text[:6000]  # cap to avoid token overload

        source = url.split("/")[2] if url.startswith("http") else "unknown"

        return Job(
            title=title,
            company="",
            location="",
            url=url,
            description=description,
            source=source,
        )
    except Exception:
        return None


async def search_jobs(query: str, location: str = "", limit: int = 5) -> list[Job]:
    """Search multiple portals. Placeholder — add portal implementations here.

    TODO:
    - jobnet.dk (Danish national job board)
    - linkedin.com/jobs
    - glassdoor.com
    """
    # For now the user provides job URLs directly
    return []
