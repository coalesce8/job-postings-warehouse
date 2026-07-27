with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2026-05-01' as date)",
        end_date="cast('2027-05-01' as date)"
    ) }}
),

final as (
    select
        date_day as full_date,
        strftime(date_day, '%Y%m%d')::int as date_key,
        date_part('day', date_day) as day_of_month,
        date_part('month', date_day) as month_of_year,
        strftime(date_day, '%B') as month_name,
        date_part('quarter', date_day) as quarter_of_year,
        date_part('year', date_day) as year_number,
        date_part('dow', date_day) as day_of_week,
        strftime(date_day, '%A') as day_name,
        date_part('dow', date_day) in (0, 6) as is_weekend
    from spine
)

select * from final
