"""Print a snapshot of both DuckDB files, for the idempotency tests in spec.md.

Usage: ``compare_state.py > before.txt``, process some dates, then
``compare_state.py > after.txt`` and ``diff before.txt after.txt``.

For every table and view it prints the row count and an order-independent checksum
of its contents; for the raw tables, also per ``pull_date``. Columns that differ on
every run without the data changing are left out (``EXCLUDE``). Opens both files
read-only, so run it while no DAG run is writing.
"""

from pathlib import Path

import duckdb

from load import require_env

# Columns whose value depends on when or where a load/build ran, not on the data.
EXCLUDE = {
    ("raw", "raw_pull_metadata"): [
        "loaded_at",    # load time
        "source_file",  # absolute path: differs between the clone and a working copy
    ],
    ("analytics", "fct_job_postings"): ["dbt_updated_at"],  # dbt's run_started_at
}


def tables(con, catalog):
    return [row[0] for row in con.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_catalog = ? AND table_schema = 'main'
        ORDER BY table_name
    """, [catalog]).fetchall()]


def checksum_query(catalog, table, where=""):
    exclude = EXCLUDE.get(("raw" if catalog == "raw" else "analytics", table))
    columns = f"* EXCLUDE ({', '.join(exclude)})" if exclude else "*"
    # hash(t) hashes the whole row; summing the hashes ignores row order but, unlike
    # XOR, still notices a duplicated row. hugeint so the sum can't overflow.
    return f"""
        SELECT count(*), coalesce(sum(hash(t)::HUGEINT), 0)
        FROM (SELECT {columns} FROM "{catalog}".main."{table}" {where}) AS t
    """


def snapshot(con, label, catalog):
    for table in tables(con, catalog):
        rows, checksum = con.execute(checksum_query(catalog, table)).fetchone()
        print(f"{label} {table} rows={rows} checksum={checksum}")


def snapshot_raw_by_date(con):
    dates = [row[0] for row in con.execute(
        "SELECT DISTINCT pull_date FROM raw.main.raw_pull_metadata ORDER BY 1"
    ).fetchall()]
    # raw_jobs has no pull_date; its rows for a date are found via pull_id, as in load.py.
    where = {
        "raw_pull_metadata": "WHERE pull_date = ?",
        "raw_jobs": "WHERE pull_id IN (SELECT pull_id FROM raw.main.raw_pull_metadata WHERE pull_date = ?)",
    }
    for d in dates:
        for table, clause in where.items():
            rows, checksum = con.execute(checksum_query("raw", table, clause), [d]).fetchone()
            print(f"raw {table} pull_date={d} rows={rows} checksum={checksum}")


def main():
    raw_path = Path(require_env("JOBS_RAW_DB_PATH"))
    analytics_path = Path(require_env("JOBS_ANALYTICS_DB_PATH"))

    if not raw_path.exists():
        print("raw missing")
        return
    if not analytics_path.exists():
        # Raw only, e.g. a load ran but no dbt build yet.
        con = duckdb.connect(":memory:")
        analytics = None
        print("analytics missing")
    else:
        con = duckdb.connect(str(analytics_path), read_only=True)
        analytics = con.execute("SELECT current_database()").fetchone()[0]
    # Same alias as profiles.yml, so the dbt views' references to "raw" resolve.
    con.execute(f"ATTACH '{raw_path}' AS raw (READ_ONLY)")

    snapshot(con, "raw", "raw")
    snapshot_raw_by_date(con)
    if analytics:
        snapshot(con, "analytics", analytics)
    con.close()


if __name__ == "__main__":
    main()
