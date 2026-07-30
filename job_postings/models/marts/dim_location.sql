with jobs as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['country', 'region', 'city', 'district']) }}
            as location_key,
        country,
        region,
        city,
        district,
        CONCAT_WS(', ', country, region, city, district),
        (country is not NULL)::int
        + (region is not NULL)::int
        + (city is not NULL)::int
        + (district is not NULL)::int as granularity_level,
        COALESCE(district, city, region, country) as lowest_level_name
    from jobs
)

select * from final
