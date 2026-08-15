with jobs as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

final as (
    select distinct
        location_key,
        country_code,
        country_name,
        area_level_2,
        area_level_3,
        area_level_4,
        granularity_level,
        lowest_level_name,
        CONCAT_WS(
            ' > ', country_name, area_level_2, area_level_3, area_level_4
        ) as location_path

    from jobs
)

select * from final
