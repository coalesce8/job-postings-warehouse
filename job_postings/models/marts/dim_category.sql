with category_pulls as (
    select * from {{ ref ('stg_adzuna__category_pulls') }}
),

jobs as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

category_pulls_agg as (
    select
        category_tag,
        any_value(category_label)     as category_label,
        min(ingested_at)    as ingested_at,
        any_value(adzuna_reported_mean_salary)     as adzuna_reported_mean_salary,
        any_value(adzuna_total_count)    as adzuna_total_count
    from category_pulls
    group by category_tag
),

category_pulls_tag_type as (
    select
        *,
        case
            when category_tag in ('graduate-jobs') then 'Career stage'
            when category_tag in ('part-time-jobs') then 'Contract type'
            when category_tag in ('charity-voluntary-jobs','consultancy-jobs') then 'Employer type'
            when category_tag in ('other-general-jobs','unknown') then 'Residual'
            else 'Occupation'
        end as tag_type
    from category_pulls_agg
),

jobs_agg as (
    select
        category_tag,
        count(*)    as rows_ingested
    from jobs
    group by category_tag
),

category_join as (
    select
        category_pulls_tag_type.category_tag,
        category_pulls_tag_type.category_label,
        category_pulls_tag_type.ingested_at,
        category_pulls_tag_type.adzuna_reported_mean_salary,
        category_pulls_tag_type.adzuna_total_count,
        category_pulls_tag_type.tag_type,
        jobs_agg.rows_ingested
    from category_pulls_tag_type
    left join jobs_agg
        on category_pulls_tag_type.category_tag = jobs_agg.category_tag
),

 final as (
    select
        *,
        {{ dbt_utils.generate_surrogate_key(['category_tag']) }} as category_key
    from category_join
)
select * from final