with stg as (
    select * from {{ ref ('stg_adzuna__jobs') }}
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
        not is_salary_predicted as is_salary_disclosed,
        is_salary_predicted,
        -- Attrs
        currency,
        contract_type,
        contract_time,
        -- Audit
        ingested_at_utc,
        '{{ run_started_at }}'::timestamp as dbt_updated_at

    from stg
)

select * from final
