with jobs as (
    select * from {{ ref('fct_job_postings') }}
),

categories as (
    select * from {{ ref('dim_category') }}
),

final as (
    select
        c.category_label,
        count(*) as postings,
        sum(j.is_salary_disclosed::int) as disclosed,
        avg(j.is_salary_disclosed::int) as disclosure_rate
    from categories as c
    left join jobs as j on c.category_key = j.category_key
    where c.tag_type = 'Occupation'
    group by c.category_key, c.category_label
)

select * from final
