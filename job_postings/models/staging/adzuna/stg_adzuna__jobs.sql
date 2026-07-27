with source as (
    select * from {{ source('adzuna', 'raw_jobs') }}
),

parsed as (
    select
        *,
        from_json(nullif(trim(location_area), ''), '["VARCHAR"]')
            as location_area_parsed
    from source
),

final as (
    select
        -- strings: trim + null-standardize
        salary_min,
        salary_max,
        ingested_at,
        nullif(trim(job_id), '') as job_id,
        nullif(trim(title), '') as job_title,
        nullif(trim(company), '') as company,
        nullif(trim(location_display), '') as location_display,
        nullif(trim(location_area_parsed[1]), '') as country,
        nullif(trim(location_area_parsed[1]), '') as region,
        nullif(trim(location_area_parsed[1]), '') as city,
        nullif(trim(location_area_parsed[1]), '') as district,
        nullif(trim(category_tag), '') as category_tag,
        nullif(trim(category_label), '') as category_label,
        nullif(trim(salary_is_predicted), '')::boolean as salary_is_predicted,
        nullif(trim(contract_time), '') as contract_time,
        nullif(trim(contract_type), '') as contract_type,
        try_cast(nullif(trim(created), '') as timestamptz) as posted_at,
        strftime(posted_at, '%Y%m%d')::int as date_key,
        nullif(trim(description), '') as job_description,
        nullif(trim(redirect_url), '') as redirect_url,
        nullif(trim(country), '') as country_code

    from parsed
)

select * from final
