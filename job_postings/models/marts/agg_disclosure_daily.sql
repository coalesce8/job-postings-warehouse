with jobs as (
    select * from {{ ref('fct_job_postings') }}
),

dates as (
    select
        date_key,
        full_date
    from {{ ref('dim_date') }}
),

countries as (
    select * from {{ ref('dim_country') }}
),

daily as (
    select
        country_code,
        posted_date_key,
        count(*) as postings,
        count(case when salary_status = 'disclosed' then 1 end) as disclosed,
        count(case when salary_status = 'predicted' then 1 end) as predicted,
        count(case when salary_status = 'absent' then 1 end) as absent
    from jobs
    group by country_code, posted_date_key
),

final as (
    select
        d.country_code,
        c.country_name,
        d.posted_date_key,
        dt.full_date as posted_date,
        d.postings,
        d.disclosed,
        d.predicted,
        d.absent,
        c.pay_transparency_effective_date,
        d.disclosed * 1.0 / d.postings as disclosure_rate,
        d.predicted * 1.0 / d.postings as predicted_rate,
        d.absent * 1.0 / d.postings as absent_rate,
        dt.full_date - c.pay_transparency_effective_date
            as days_since_pay_transparency_effective,
        dt.full_date >= c.pay_transparency_effective_date
            as is_post_pay_transparency
    from daily as d
    left join dates as dt on d.posted_date_key = dt.date_key
    left join countries as c on d.country_code = c.country_code
)

select * from final
