"""Check that one pull date of raw JSON is complete and sane before it is loaded.

Usage: ``check_raw.py --date YYYY-MM-DD``. Looks at ``$JOBS_RAW_DATA_DIR/<date>/``
and fails, naming every problem found, unless:

- there is at least one file for every code in ``ingest.COUNTRY_CODES``;
- every file parses as JSON, and its ``country`` matches its filename;
- every file's ``fetched_at`` falls on the directory's date (UTC).

A partial day must fail here rather than load, or it leaves a gap nothing points
to. Files for countries not in ``COUNTRY_CODES`` are allowed. Reads only; never
writes anything.
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dates import parse_date
from ingest import COUNTRY_CODES, require_env

# Matches the names written by ingest.write_envelope.
FILENAME_RE = re.compile(r"adzuna_(?P<country>[a-z]{2})_\d{6}\.json")

log = logging.getLogger(__name__)


def check_file(path, pull_date):
    """Return a list of problems with one file (empty if it is fine)."""
    m = FILENAME_RE.fullmatch(path.name)
    if not m:
        return [f"{path.name}: name doesn't match adzuna_<country>_<HHMMSS>.json"]

    try:
        with path.open("r", encoding="utf-8") as f:
            envelope = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return [f"{path.name}: not valid JSON ({e})"]
    if not isinstance(envelope, dict):
        return [f"{path.name}: top level is not a JSON object"]

    problems = []
    if envelope.get("country") != m["country"]:
        problems.append(
            f"{path.name}: country is {envelope.get('country')!r}, filename says {m['country']!r}"
        )

    fetched_at = envelope.get("fetched_at")
    try:
        ts = datetime.fromisoformat(fetched_at)
    except (TypeError, ValueError):
        problems.append(f"{path.name}: fetched_at is not an ISO timestamp: {fetched_at!r}")
    else:
        if ts.tzinfo is None:
            problems.append(f"{path.name}: fetched_at has no timezone: {fetched_at!r}")
        elif ts.astimezone(timezone.utc).date() != pull_date:
            problems.append(f"{path.name}: fetched_at {fetched_at} is not on {pull_date} (UTC)")
    return problems


def check_date(raw_dir, pull_date):
    """Return a list of problems with one pull date (empty if it can be loaded)."""
    date_dir = raw_dir / pull_date.isoformat()
    if not date_dir.is_dir():
        return [f"no directory {date_dir}"]

    paths = sorted(date_dir.glob("*.json"))
    problems = []
    for path in paths:
        problems.extend(check_file(path, pull_date))

    countries = {m["country"] for p in paths if (m := FILENAME_RE.fullmatch(p.name))}
    missing = [c for c in COUNTRY_CODES if c not in countries]
    if missing:
        problems.append(f"no file for {', '.join(missing)} (expected {', '.join(COUNTRY_CODES)})")
    return problems


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", required=True, type=parse_date, help="pull date, YYYY-MM-DD")
    args = parser.parse_args()

    raw_dir = Path(require_env("JOBS_RAW_DATA_DIR"))
    problems = check_date(raw_dir, args.date)
    if problems:
        for problem in problems:
            log.error("%s", problem)
        log.error("%s failed the check, problems: %d", args.date, len(problems))
        sys.exit(1)
    log.info("%s OK", args.date)


if __name__ == "__main__":
    main()
