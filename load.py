"""Load the JSON envelopes written by ``ingest.py`` into the raw DuckDB database.

Every ``*.json`` under ``$JOBS_RAW_DATA_DIR`` is a pull. Its ``pull_id`` is derived
from the path (``<YYYY-MM-DD>_<file stem>``), so re-running is idempotent: pulls
already present in ``raw_pull_metadata`` are skipped, and each new pull is loaded in
a single transaction.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

log = logging.getLogger(__name__)


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Set the {name} environment variable (see .env.example)")
    return value


def get_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_pull_metadata (
            pull_id             VARCHAR PRIMARY KEY,  -- derived from filename, deterministic
            fetched_at          TIMESTAMP,
            country_code        VARCHAR,
            max_days_old        INTEGER,
            sort_by             VARCHAR,
            search_params       VARCHAR,              -- full params dict as JSON
            max_pages           INTEGER,              -- client-side cap on pages requested
            pages_with_results  INTEGER,
            total_count         INTEGER,              -- Adzuna's `count` for this query
            mean_salary         DOUBLE,               -- Adzuna's `mean` for this query
            source_file         VARCHAR,
            loaded_at           TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_jobs (
            pull_id              VARCHAR,
            job_id               VARCHAR,
            title                VARCHAR,
            company              VARCHAR,
            location_display     VARCHAR,
            location_area        VARCHAR,
            latitude             DOUBLE,
            longitude            DOUBLE,
            category_tag         VARCHAR,
            category_label       VARCHAR,
            salary_min           DOUBLE,
            salary_max           DOUBLE,
            salary_is_predicted  VARCHAR,
            contract_time        VARCHAR,
            contract_type        VARCHAR,
            created              VARCHAR,
            description          VARCHAR,
            redirect_url         VARCHAR,
            PRIMARY KEY (pull_id, job_id)
        )
    """)
    return con


def pull_id_for(path):
    return f"{path.parent.name}_{path.stem}"


def loaded_pull_ids(con):
    return {row[0] for row in con.execute("SELECT pull_id FROM raw_pull_metadata").fetchall()}


def insert_metadata(con, pull_id, envelope, source_file):
    params = envelope.get("params", {})
    con.execute("""
        INSERT INTO raw_pull_metadata (
            pull_id, fetched_at, country_code, max_days_old, sort_by, search_params,
            max_pages, pages_with_results, total_count, mean_salary, source_file, loaded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        pull_id,
        envelope.get("fetched_at"),
        envelope["country"],
        params.get("max_days_old"),
        params.get("sort_by"),
        json.dumps(params, ensure_ascii=False),
        envelope.get("max_pages"),
        envelope.get("pages_with_results"),
        envelope.get("count"),
        envelope.get("mean"),
        str(source_file),
        datetime.now(timezone.utc),
    ])


def insert_jobs(con, pull_id, jobs):
    rows = []
    for job in jobs:
        company = job.get("company") or {}
        location = job.get("location") or {}
        category = job.get("category") or {}
        rows.append((
            pull_id,
            job.get("id"),
            job.get("title"),
            company.get("display_name"),
            location.get("display_name"),
            json.dumps(location.get("area", []), ensure_ascii=False),
            job.get("latitude"),
            job.get("longitude"),
            category.get("tag"),
            category.get("label"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("salary_is_predicted"),
            job.get("contract_time"),
            job.get("contract_type"),
            job.get("created"),
            job.get("description"),
            job.get("redirect_url"),
        ))
    if not rows:
        return
    con.executemany("""
        INSERT INTO raw_jobs (
            pull_id, job_id, title, company, location_display, location_area,
            latitude, longitude, category_tag, category_label,
            salary_min, salary_max, salary_is_predicted,
            contract_time, contract_type,
            created, description, redirect_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING
    """, rows)


def load_file(con, path):
    """Load one envelope atomically; returns the number of jobs in the file."""
    with path.open("r", encoding="utf-8") as f:
        envelope = json.load(f)

    pull_id = pull_id_for(path)
    jobs = envelope.get("results", [])

    con.begin()
    try:
        insert_metadata(con, pull_id, envelope, path)
        insert_jobs(con, pull_id, jobs)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return len(jobs)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    raw_dir = Path(require_env("JOBS_RAW_DATA_DIR"))
    db_path = Path(require_env("JOBS_RAW_DB_PATH"))

    con = get_db(db_path)
    failed = []
    try:
        already_loaded = loaded_pull_ids(con)
        for path in sorted(raw_dir.rglob("*.json")):
            if pull_id_for(path) in already_loaded:
                continue
            log.info("Loading %s ...", path)
            try:
                n = load_file(con, path)
            except (json.JSONDecodeError, KeyError, duckdb.Error) as e:
                log.error("Failed to load %s: %r", path, e)
                failed.append(path)
                continue
            log.info("Loaded %d jobs", n)
    finally:
        con.close()

    if failed:
        log.error("Failed files: %s", ", ".join(str(p) for p in failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
