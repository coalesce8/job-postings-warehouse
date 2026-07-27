with category_pulls as (
    select * from {{ ref ('stg_adzuna__category_pulls') }}
),

category_pulls_agg as (
    select
        category_tag,   
        any_value(category_label)     as category_label,
        any_value(adzuna_reported_mean_salary)     as adzuna_reported_mean_salary,
        any_value(adzuna_total_count)    as adzuna_total_count,
        case
            when category_tag in ('graduate-jobs') then 'Career stage'
            when category_tag in ('part-time-jobs') then 'Contract type'
            when category_tag in ('charity-voluntary-jobs','consultancy-jobs') then 'Employer type'
            when category_tag in ('other-general-jobs','unknown') then 'Residual'
            else 'Occupation'
        end as tag_type
    from category_pulls
    group by category_tag
),

 final as (
    select
        *,
        {{ dbt_utils.generate_surrogate_key(['category_tag']) }} as category_key
    from category_pulls_agg
)
select * from final