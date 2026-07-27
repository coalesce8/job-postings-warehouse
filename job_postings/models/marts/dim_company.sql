with final as (
    select company from {{ ref ('stg_adzuna__jobs') }}
)

select * from final
