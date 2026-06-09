#!/usr/bin/env python3
"""
Tracker for seen job postings in Jabba's daily digest.
Prevents showing the same vacancy twice.

Usage:
  python3 tracker.py check --urls URL1 URL2 ...   # returns JSON: {"new": [urls not seen before]}
  python3 tracker.py mark  --urls URL1 URL2 ...   # marks URLs as seen, returns {"marked": N}
  python3 tracker.py stats                         # returns total seen count and oldest entry
  python3 tracker.py clean --days 90              # removes entries older than N days
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

STORAGE_PATH = Path("/root/.hermes/profiles/jabba/data/seen_jobs.json")


def load_db() -> dict:
    if STORAGE_PATH.exists():
        try:
            with open(STORAGE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_db(db: dict) -> None:
    STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORAGE_PATH, "w") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def cmd_check(urls: list[str]) -> None:
    db = load_db()
    new_urls = [u for u in urls if u not in db]
    print(json.dumps({"new": new_urls, "already_seen": len(urls) - len(new_urls)}))


def cmd_mark(urls: list[str]) -> None:
    db = load_db()
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for url in urls:
        if url not in db:
            db[url] = now
            count += 1
    save_db(db)
    print(json.dumps({"marked": count, "total_in_db": len(db)}))


def cmd_stats() -> None:
    db = load_db()
    if not db:
        print(json.dumps({"total": 0, "oldest": None, "newest": None}))
        return
    dates = sorted(db.values())
    print(json.dumps({
        "total": len(db),
        "oldest": dates[0],
        "newest": dates[-1],
    }))


def cmd_clean(days: int) -> None:
    db = load_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    before = len(db)
    db = {url: ts for url, ts in db.items() if ts >= cutoff_str}
    save_db(db)
    removed = before - len(db)
    print(json.dumps({"removed": removed, "remaining": len(db)}))


def main():
    parser = argparse.ArgumentParser(description="Track seen job postings for daily digest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_p = subparsers.add_parser("check", help="Filter out already-seen URLs")
    check_p.add_argument("--urls", nargs="+", required=True)

    mark_p = subparsers.add_parser("mark", help="Mark URLs as seen")
    mark_p.add_argument("--urls", nargs="+", required=True)

    subparsers.add_parser("stats", help="Show database statistics")

    clean_p = subparsers.add_parser("clean", help="Remove old entries")
    clean_p.add_argument("--days", type=int, default=90)

    args = parser.parse_args()

    if args.command == "check":
        cmd_check(args.urls)
    elif args.command == "mark":
        cmd_mark(args.urls)
    elif args.command == "stats":
        cmd_stats()
    elif args.command == "clean":
        cmd_clean(args.days)


if __name__ == "__main__":
    main()
