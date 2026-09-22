"""Pull recent job postings from the Adzuna API and write one JSON file per country.

Files are written to ``$JOBS_RAW_DATA_DIR/<YYYY-MM-DD>/adzuna_<country>_<HHMMSS>.json``
(UTC). Each file is an envelope::

    {
      "fetched_at": "<ISO-8601 UTC>",
      "country": "<two-letter code>",
      "params": {<search params sent to the API, credentials excluded>},
      "count": <Adzuna's total match count>,
      "mean": <Adzuna's mean salary for the query>,
      "max_pages": <client-side cap on pages requested>,
      "pages_with_results": <number of pages that returned at least one job>,
      "results": [<job objects as returned by the API>]
    }

``load.py`` reads these files into DuckDB.

Rate limits: the free tier allows roughly 25 calls per minute and a fixed daily
budget, so ``REQUEST_DELAY_SECONDS`` spaces calls out and ``MAX_PAGES`` is sized so
that ``len(COUNTRY_CODES) * MAX_PAGES`` stays within the daily budget. A 429 aborts
the whole run immediately rather than retrying: retries count against the cap, and
a partially fetched country is not written.

Set ``COUNTRIES`` (comma-separated codes, e.g. ``COUNTRIES=gb,pl``) to pull a subset
of ``COUNTRY_CODES``, for re-running only the countries that failed in a daily run.
"""

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

RESULTS_PER_PAGE = 50
MAX_DAYS_OLD = 1
MAX_PAGES = 14  # 700 jobs max per country; 5 countries * 14 = 70 calls/day
REQUEST_DELAY_SECONDS = 2.5  # stays under 25 calls/minute

SEARCH_PARAMS = {
    "results_per_page": RESULTS_PER_PAGE,
    "max_days_old": MAX_DAYS_OLD,
    "sort_by": "date",
}

# Adzuna carries no salary data at all for its German-language markets (de,
# at: 0 of 700 postings had a salary, even though Austrian law requires one in
# the ad), nor for fr; be salaries are unparsed daily/monthly rates. Those
# markets were checked on 2026-09-21 and left out.
COUNTRY_CODES = [
    "gb",  # United Kingdom
    "it",  # Italy
    "nl",  # Netherlands
    "es",  # Spain
    "pl",  # Poland
]

log = logging.getLogger(__name__)


class RateLimited(Exception):
    """Adzuna returned HTTP 429; the daily or per-minute quota is exhausted."""


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Set the {name} environment variable (see .env.example)")
    return value


def selected_countries(spec):
    """Parse a ``COUNTRIES`` override; unset or blank means all of ``COUNTRY_CODES``."""
    if not spec or not spec.strip():
        return COUNTRY_CODES
    codes = [c.strip().lower() for c in spec.split(",") if c.strip()]
    unknown = sorted(set(codes) - set(COUNTRY_CODES))
    if unknown:
        raise SystemExit(
            f"Unknown country code(s) in COUNTRIES: {', '.join(unknown)} "
            f"(known: {', '.join(COUNTRY_CODES)})"
        )
    return codes


def fetch_page(country, page, auth):
    resp = requests.get(
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}",
        params={**SEARCH_PARAMS, **auth},
        timeout=30,
    )
    if resp.status_code == 429:
        raise RateLimited(f"{country} page {page}: {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()


def fetch_jobs(country, auth):
    """Fetch up to MAX_PAGES of results for a country and return the envelope."""
    fetched_at = datetime.now(timezone.utc)

    data = fetch_page(country, 1, auth)
    count = data.get("count", 0)
    mean = data.get("mean")
    results = list(data.get("results", []))
    pages_with_results = 1 if results else 0

    total_pages = min(max(1, math.ceil(count / RESULTS_PER_PAGE)), MAX_PAGES)
    for page in range(2, total_pages + 1):
        time.sleep(REQUEST_DELAY_SECONDS)
        page_results = fetch_page(country, page, auth).get("results", [])
        if not page_results:
            break
        results.extend(page_results)
        pages_with_results += 1

    return {
        "fetched_at": fetched_at.isoformat(),
        "country": country,
        "params": SEARCH_PARAMS,
        "count": count,
        "mean": mean,
        "max_pages": MAX_PAGES,
        "pages_with_results": pages_with_results,
        "results": results,
    }


def write_envelope(envelope, raw_dir):
    fetched_at = datetime.fromisoformat(envelope["fetched_at"])
    out_dir = raw_dir / fetched_at.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"adzuna_{envelope['country']}_{fetched_at.strftime('%H%M%S')}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)
    return out_path


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    auth = {
        "app_id": require_env("ADZUNA_APP_ID"),
        "app_key": require_env("ADZUNA_APP_KEY"),
    }
    raw_dir = Path(require_env("JOBS_RAW_DATA_DIR"))
    countries = selected_countries(os.environ.get("COUNTRIES"))

    failed = []
    for i, country in enumerate(countries):
        if i:
            time.sleep(REQUEST_DELAY_SECONDS)
        log.info("Fetching jobs for %s ...", country)
        try:
            envelope = fetch_jobs(country, auth)
        except RateLimited as e:
            # Don't move on to the next country: every further call would also
            # fail and still count against the quota.
            log.error("Rate limited, aborting run: %s", e)
            failed.extend(countries[i:])
            break
        except (requests.RequestException, json.JSONDecodeError) as e:
            log.error("Failed to fetch %s: %s", country, e)
            failed.append(country)
            continue
        out_path = write_envelope(envelope, raw_dir)
        log.info("Wrote %d jobs to %s", len(envelope["results"]), out_path)

    if failed:
        log.error("Failed countries: %s", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
