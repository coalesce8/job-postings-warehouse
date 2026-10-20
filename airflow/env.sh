# Airflow environment for this project. Source it, don't run it:
#   source airflow/env.sh
# then use `airflow ...` (e.g. `airflow standalone`) in the same shell.

# Directory of this file, whether sourced from bash or zsh.
if [ -n "$ZSH_VERSION" ]; then
    _airflow_dir="${${(%):-%x}:A:h}"
else
    _airflow_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# standalone starts its components as `airflow` subprocesses, so the venv must be on PATH.
export PATH="$_airflow_dir/.venv/bin:$PATH"

# Metadata DB, config and logs live outside the repo.
export AIRFLOW_HOME="$HOME/airflow"
# Holds symlinks into Airflow's clone, so Airflow only runs code that is on main.
export AIRFLOW__CORE__DAGS_FOLDER="$AIRFLOW_HOME/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False

# Read by the DAG's tasks. Airflow's own clone, never this working copy; tasks run
# its scripts with its project venv, so the Airflow venv never needs DuckDB or dbt.
export REPO_DIR="$AIRFLOW_HOME/repo"
export PROJECT_PYTHON="$REPO_DIR/.venv/bin/python"
export PROJECT_DBT="$REPO_DIR/.venv/bin/dbt"
# Same names as .env, used by load.py and profiles.yml. Raw JSON comes from the
# clone; both DuckDB files live outside it, so a git pull never touches them.
export JOBS_RAW_DATA_DIR="$REPO_DIR/data/raw"
export JOBS_RAW_DB_PATH="$AIRFLOW_HOME/data/jobs_raw.duckdb"
export JOBS_ANALYTICS_DB_PATH="$AIRFLOW_HOME/data/jobs_analytics.duckdb"

unset _airflow_dir
