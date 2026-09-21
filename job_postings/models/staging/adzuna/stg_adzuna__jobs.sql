with jobs as (
    select * from {{ source('adzuna', 'raw_jobs') }}
),

pulls as (
    select
        pull_id,
        fetched_at,
        country_code
    from {{ source('adzuna', 'raw_pull_metadata') }}
),

countries as (
    select
        country_code,
        currency,
        timezone
    from {{ ref('country_codes') }}
),

source as (
    select
        j.*,
        p.fetched_at,
        p.country_code,
        c.currency,
        c.timezone as market_timezone
    from jobs as j
    left join pulls as p on j.pull_id = p.pull_id
    left join countries as c on p.country_code = c.country_code
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
        -- Adzuna stamps `created` with a Z but the value is wall-clock time
        -- in the market's own timezone (it runs ahead of the UTC fetch
        -- time). Cast to a naive timestamp so the wall-clock value is kept;
        -- the UTC version is derived below using the seed's timezone.
        try_cast(nullif(trim(created), '') as timestamp) as posted_at_local

    from parsed
),

utc as (
    select
        *,
        -- interpret the local wall-clock time in the market's timezone,
        -- then express it as naive UTC
        timezone(market_timezone, posted_at_local) at time zone 'UTC'
            as posted_at_utc
    from cleaned
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
    from utc
),

keys as (
    select
        *,
        {{ dbt_utils.generate_surrogate_key(['country_name', 'area_level_2', 'area_level_3', 'area_level_4']) }}
            as location_key
    from location_features
),

final as (
    select
        salary_min,
        salary_max,
        company_name,
        granularity_level,
        lowest_level_name,
        posted_at_utc,
        posted_at_local,
        market_timezone,
        location_key,
        country_code,
        country_name,
        fetched_at,
        currency,
        nullif(trim(pull_id), '') as pull_id,
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
        nullif(trim(description), '') as job_description,
        nullif(trim(redirect_url), '') as redirect_url

    from keys
)

select * from final
