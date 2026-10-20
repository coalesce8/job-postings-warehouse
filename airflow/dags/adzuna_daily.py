"""Process one pull date of raw Adzuna JSON: sync → check → load → dbt build.

M1: the date is hardcoded, check_raw only checks the directory exists, and
load_raw runs the no-argument load.py (every date not yet loaded). M2 replaces
all three with the per-date versions.

Every task shells out to a script in Airflow's clone ($REPO_DIR), run with the
clone's own project venv ($PROJECT_PYTHON, $PROJECT_DBT), not Airflow's
venv, so each one also runs from a terminal with no Airflow. Paths come from the
environment (see airflow/env.sh), never from this file.
"""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

# M1 only. M2 derives this from params.run_date or the run's logical date.
RUN_DATE = "2026-10-10"

with DAG(
    "adzuna_daily",
    schedule="0 20 * * *",  # ~4.5 h after the Action normally lands
    start_date=datetime(2026, 9, 22),
    catchup=False,  # history goes through explicit backfills
    max_active_runs=1,  # one DuckDB writer at a time
    default_args={"retries": 0},  # check, load and dbt failures are deterministic
    tags=["adzuna"],
) as dag:
    # RUN_DATE goes through env, not the command string: from M2 it can come
    # from params, i.e. user input, and templated bash isn't escaped.
    # append_env keeps REPO_DIR, PROJECT_* and JOBS_* from the parent.
    run_env = {"RUN_DATE": RUN_DATE}

    sync_raw = BashOperator(
        task_id="sync_raw",
        bash_command='git -C "$REPO_DIR" pull --ff-only && cd "$REPO_DIR" && uv sync --frozen',
        retries=2,  # network errors are transient
        retry_delay=timedelta(minutes=5),
    )

    check_raw = BashOperator(
        task_id="check_raw",
        # Placeholder until check_raw.py (M2).
        bash_command='test -d "$JOBS_RAW_DATA_DIR/$RUN_DATE" || { echo "No raw directory for $RUN_DATE"; exit 1; }',
        env=run_env,
        append_env=True,
    )

    load_raw = BashOperator(
        task_id="load_raw",
        bash_command='cd "$REPO_DIR" && "$PROJECT_PYTHON" load.py',
        env=run_env,
        append_env=True,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            '"$PROJECT_DBT" build'
            ' --project-dir "$REPO_DIR/job_postings"'
            ' --profiles-dir "$REPO_DIR/job_postings"'
        ),
        env=run_env,
        append_env=True,
    )

    sync_raw >> check_raw >> load_raw >> dbt_build
