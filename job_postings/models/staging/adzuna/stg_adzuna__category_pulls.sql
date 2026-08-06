with source as (
    select * from {{ source('adzuna', 'raw_jobs') }}
),

final as (
    select
        mean as adzuna_reported_mean_salary,
        count as adzuna_total_count,
        nullif(trim(category_tag), '') as category_tag,
        nullif(trim(category_label), '') as category_label
    from source
    group by all
)

select * from final
