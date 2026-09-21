with stg as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

-- The same job can be returned by several daily pulls. Rank each job's
-- observations so the next CTE can keep only the first one.
observations as (
    select
        *,
        row_number() over (
            partition by job_id order by fetched_at, pull_id
        ) as observation_rank,
        count(*) over (partition by job_id) as times_seen
    from stg
),

first_seen as (
    select
        *,
        case
            when is_salary_predicted then 'predicted'
            when salary_min is not null or salary_max is not null
                then 'disclosed'
            else 'absent'
        end as salary_status
    from observations
    where observation_rank = 1
),

final as (
    select
        -- PK
        job_id,
        -- DD
        job_title,
        redirect_url,
        -- FK
        category_tag as category_key,
        company_key,
        location_key,
        country_code,
        strftime(posted_at_utc::date, '%Y%m%d')::int as posted_date_key,
        -- Measure
        salary_min,
        salary_max,
        (salary_min + salary_max) / 2.0 as salary_mid,
        case
            when salary_min is not null and salary_max is not null then 'both'
            when salary_min is null and salary_max is not null then 'max_only'
            when salary_min is not null and salary_max is null then 'min_only'
            else 'none' end
            as salary_bounds_available,
        salary_max - salary_min as salary_range_width,
        -- flag
        salary_status,
        salary_status = 'disclosed' as is_salary_disclosed,
        is_salary_predicted,
        -- Attrs
        currency,
        contract_type,
        contract_time,
        -- Audit
        fetched_at as first_fetched_at,
        times_seen,
        '{{ run_started_at }}'::timestamp as dbt_updated_at

    from first_seen
)

select * from final
