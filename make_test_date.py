"""Make a test pull date by copying a real one, for the acceptance tests in spec.md.

Usage: ``make_test_date.py --from-dir data/raw/2026-10-19 --to-dir <test raw dir>/2099-01-01``.

Copies every ``*.json`` in ``--from-dir`` to ``--to-dir`` under the same name, and
moves each file's ``fetched_at`` to the date in ``--to-dir``'s name, keeping the
time of day. The copy is then a valid day that passes ``check_raw.py``, so each test
can break exactly one thing and that one thing is the only reason it fails.

Test dates must never be committed, so ``--to-dir`` may not be inside the repo, and
an existing ``--to-dir`` is never overwritten.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-dir", required=True, type=Path, help="a real date directory")
    parser.add_argument("--to-dir", required=True, type=Path, help="<test raw dir>/<YYYY-MM-DD>")
    args = parser.parse_args()

    to_dir = args.to_dir.resolve()
    try:
        test_date = date.fromisoformat(to_dir.name)
    except ValueError:
        sys.exit(f"--to-dir must end in a YYYY-MM-DD directory: {to_dir}")
    if to_dir.is_relative_to(REPO_DIR):
        sys.exit(f"--to-dir must be outside the repo, test dates are never committed: {to_dir}")
    if to_dir.exists():
        sys.exit(f"--to-dir already exists, remove it first: {to_dir}")

    paths = sorted(args.from_dir.glob("*.json"))
    if not paths:
        sys.exit(f"no *.json in {args.from_dir}")

    to_dir.mkdir(parents=True)
    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            envelope = json.load(f)
        fetched_at = datetime.fromisoformat(envelope["fetched_at"])
        envelope["fetched_at"] = datetime.combine(test_date, fetched_at.timetz()).isoformat()
        # Same format as ingest.write_envelope.
        with (to_dir / path.name).open("w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=2)
        print(f"{to_dir / path.name}: fetched_at {envelope['fetched_at']}")


if __name__ == "__main__":
    main()
