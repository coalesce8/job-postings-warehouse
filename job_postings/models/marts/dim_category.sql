with category_pulls as (
    select * from {{ ref ('stg_adzuna__category_pulls') }}
),

final as (
    select
        category_tag as category_key,
        category_label,
        adzuna_reported_mean_salary,
        adzuna_total_count,
        case
            when category_tag in ('graduate-jobs') then 'Career stage'
            when category_tag in ('part-time-jobs') then 'Contract type'
            when
                category_tag in ('charity-voluntary-jobs', 'consultancy-jobs')
                then 'Employer type'
            when
                category_tag in ('other-general-jobs', 'unknown')
                then 'Residual'
            else 'Occupation'
        end as tag_type
    from category_pulls
)

select * from final
