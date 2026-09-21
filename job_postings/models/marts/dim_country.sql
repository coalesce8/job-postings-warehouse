with countries as (
    select * from {{ ref('country_codes') }}
),

final as (
    select
        country_code,
        country_name,
        currency,
        timezone,
        is_eu_member,
        pay_transparency_effective_date,
        requires_pay_in_job_ad,
        legislation_notes,
        legislation_checked_on,
        -- Directive (EU) 2023/970, Art. 34: member states had until this
        -- date to transpose. Kept here as a reference line for plots.
        cast('2026-06-07' as date) as eu_directive_transposition_deadline,
        pay_transparency_effective_date is not null
            as has_pay_transparency_rules
    from countries
)

select * from final
