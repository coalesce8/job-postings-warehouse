with jobs as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

final as (
    select distinct
        {{ dbt_utils.generate_surrogate_key(['country_name', 'region', 'city', 'district']) }}
            as location_key,
        country_name,
        region,
        city,
        district,
        CONCAT_WS('>', country_name, region, city, district) as location_path,
        granularity_level,
        lowest_level_name

    from jobs
)

select * from final
