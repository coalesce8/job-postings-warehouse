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

cleaned as (
    select
        *,
        nullif(trim(company), '') as company_name,
        nullif(trim(location_area_parsed[1]), '') as country_name,
        nullif(trim(location_area_parsed[2]), '') as area_level_2,
        nullif(trim(location_area_parsed[3]), '') as area_level_3,
        nullif(trim(location_area_parsed[4]), '') as area_level_4,
        try_cast(nullif(trim(created), '') as timestamptz) at time zone 'UTC'
            as posted_at_utc,
        nullif(trim(country), '') as country_code

    from parsed
),

location_features as (
    select
        *,
        (country_name is not NULL)::int
        + (area_level_2 is not NULL)::int
        + (area_level_3 is not NULL)::int
        + (area_level_4 is not NULL)::int as granularity_level,
        coalesce(area_level_4, area_level_3, area_level_2, country_name)
            as lowest_level_name
    from cleaned
),

keys as (
    select
        *,
        {{ dbt_utils.generate_surrogate_key(['country_name', 'area_level_2', 'area_level_3', 'area_level_4']) }}
            as location_key
    from location_features
),

jobs_currency as (
    select
        *,
        case when country_code = 'gb' then 'GBP' else 'UNKNOWN' end as currency
    from keys
),


final as (
    select
        salary_min,
        salary_max,
        company_name,
        granularity_level,
        lowest_level_name,
        posted_at_utc,
        location_key,
        currency,
        country_code,
        country_name,
        ingested_at at time zone 'UTC' as ingested_at_utc,
        nullif(trim(job_id), '') as job_id,
        nullif(trim(title), '') as job_title,
        coalesce(lower(company_name), '__UNKNOWN__') as company_key,
        nullif(trim(location_display), '') as location_display,
        coalesce(area_level_2, '__UNKNOWN__') as area_level_2,
        coalesce(area_level_3, '__UNKNOWN__') as area_level_3,
        coalesce(area_level_4, '__UNKNOWN__') as area_level_4,
        nullif(trim(category_tag), '') as category_tag,
        nullif(trim(category_label), '') as category_label,
        nullif(trim(salary_is_predicted), '')::boolean as is_salary_predicted,
        nullif(trim(contract_time), '') as contract_time,
        nullif(trim(contract_type), '') as contract_type,
        strftime(posted_at_utc, '%Y%m%d')::int as date_key,
        nullif(trim(description), '') as job_description,
        nullif(trim(redirect_url), '') as redirect_url

    from jobs_currency
)

select * from final
