with jobs as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

-- Tags are shared across Adzuna markets but labels are localised;
-- prefer the UK (English) label, falling back to any label for tags
-- only seen in other markets.
categories as (
    select
        category_tag,
        coalesce(
            max(case when country_code = 'gb' then category_label end),
            max(category_label)
        ) as category_label
    from jobs
    group by category_tag
),

final as (
    select
        category_tag as category_key,
        category_label,
        case
            when category_tag in ('graduate-jobs') then 'Career stage'
            when category_tag in ('part-time-jobs') then 'Contract type'
            when
                category_tag in ('charity-voluntary-jobs', 'consultancy-jobs')
                then 'Employer type'
            when
                category_tag in ('other-general-jobs', 'unknown')
                then 'Residual'
            when
                category_tag in (
                    'accounting-finance-jobs',
                    'it-jobs',
                    'sales-jobs',
                    'customer-services-jobs',
                    'engineering-jobs',
                    'hr-jobs',
                    'healthcare-nursing-jobs',
                    'hospitality-catering-jobs',
                    'pr-advertising-marketing-jobs',
                    'logistics-warehouse-jobs',
                    'teaching-jobs',
                    'trade-construction-jobs',
                    'admin-jobs',
                    'legal-jobs',
                    'creative-design-jobs',
                    'retail-jobs',
                    'manufacturing-jobs',
                    'scientific-qa-jobs',
                    'social-work-jobs',
                    'travel-jobs',
                    'energy-oil-gas-jobs',
                    'property-jobs',
                    'domestic-help-cleaning-jobs',
                    'maintenance-jobs'
                )
                then 'Occupation'
        end as tag_type
    from categories
)

select * from final
