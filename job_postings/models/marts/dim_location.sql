with jobs as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

final as (
    select distinct
        location_key,
        country_name,
        region,
        city,
        district,
        granularity_level,
        lowest_level_name,
        CONCAT_WS(' > ', country_name, region, city, district) as location_path

    from jobs
)

select * from final
