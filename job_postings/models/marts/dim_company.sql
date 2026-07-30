with jobs as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

final as (
    select
        company_key,
        max(company_name) as company_name
    from jobs
    group by company_key
)

select * from final
