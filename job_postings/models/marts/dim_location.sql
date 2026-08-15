with jobs as (
    select * from {{ ref ('stg_adzuna__jobs') }}
),

final as (
    select distinct
        location_key,
        area_level_1,
        area_level_2,
        area_level_3,
        area_level_4,
        granularity_level,
        lowest_level_name,
        CONCAT_WS(' > ', area_level_1, area_level_2, area_level_3, area_level_4) as location_path

    from jobs
)

select * from final
