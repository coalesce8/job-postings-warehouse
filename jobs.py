import os
import json
import time
import pathlib
from datetime import datetime, timezone

import duckdb
import requests


APP_ID = os.environ.get("ADZUNA_APP_ID", "")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")

RESULTS_PER_PAGE = 50
MAX_DAYS_OLD = 30
MAX_PAGES = 1     # 500 jobs max per country
SEARCH_PARAMS = {"what_or": "dbt snowflake bigquery redshift databricks duckdb fivetran airflow ETL ELT"}

COUNTRY_CODES = [
    "gb",  # United Kingdom
]


def get_db(path: str = "data/jobs.duckdb"):
    pathlib.Path(path).parent.mkdir(exist_ok=True)
    con = duckdb.connect(path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_jobs (
            job_id              VARCHAR PRIMARY KEY,
            title               VARCHAR,
            company             VARCHAR,
            location_display    VARCHAR,
            location_area       VARCHAR,
            latitude            DOUBLE,
            longitude           DOUBLE,
            category_tag        VARCHAR,
            category_label      VARCHAR,
            salary_min          DOUBLE,
            salary_max          DOUBLE,
            salary_is_predicted VARCHAR,
            contract_time       VARCHAR,
            contract_type       VARCHAR,
            created             VARCHAR,
            description         VARCHAR,
            redirect_url        VARCHAR,
            country             VARCHAR,
            page                INT,
            search_params       VARCHAR,
            mean                DOUBLE,
            count               INT,
            ingested_at         TIMESTAMP WITH TIME ZONE
        )
    """)
    return con


def insert_jobs(con, jobs, country, search_params, page, mean, count):
    now = datetime.now(timezone.utc)
    rows = [
        (
            job.get("id"),
            job.get("title"),
            job.get("company", {}).get("display_name"),
            job.get("location", {}).get("display_name"),
            json.dumps(job.get("location", {}).get("area", []), ensure_ascii=False),
            job.get("latitude"),
            job.get("longitude"),
            job.get("category", {}).get("tag"),
            job.get("category", {}).get("label"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("salary_is_predicted"),
            job.get("contract_time"),
            job.get("contract_type"),
            job.get("created"),
            job.get("description"),
            job.get("redirect_url"),
            country,
            page,
            json.dumps(search_params, ensure_ascii=False),
            mean,
            count,
            now,
        )
        for job in jobs
    ]
    con.executemany("""
        INSERT INTO raw_jobs (
            job_id, title, company, location_display, location_area,
            latitude, longitude, category_tag, category_label,
            salary_min, salary_max, salary_is_predicted,
            contract_time, contract_type,
            created, description, redirect_url,
            country, page, search_params, mean, count, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING
    """, rows)


def fetch_page(country, page, params):
    resp = requests.get(
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}",
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_jobs(con, country, params):
    data = fetch_page(country, 1, params)

    mean_salary = data.get("mean")
    total_results = data.get("count", 0)
    total_pages = min((total_results // RESULTS_PER_PAGE) + 1, MAX_PAGES)

    jobs = data.get("results", [])
    if jobs:
        insert_jobs(con, jobs, country, SEARCH_PARAMS, 1, mean_salary, total_results)

    for page in range(2, total_pages + 1):
        time.sleep(0.5)
        data = fetch_page(country, page, params)
        jobs = data.get("results", [])
        if not jobs:
            break
        insert_jobs(con, jobs, country, SEARCH_PARAMS, page, mean_salary, total_results)

def main():
    if not APP_ID or not APP_KEY:
        raise ValueError("Set ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables")

    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "max_days_old": MAX_DAYS_OLD,
        **SEARCH_PARAMS,
    }

    con = get_db()
    try:
        for country in COUNTRY_CODES:
            print(f"Fetching jobs for {country}...")
            try:
                fetch_jobs(con, country, params)
            except requests.HTTPError as e:
                print(f"  HTTP error for {country}: {e}")
            except requests.RequestException as e:
                print(f"  Network error for {country}: {e}")
            except json.JSONDecodeError as e:
                print(f"  JSON decode error for {country}: {e}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
