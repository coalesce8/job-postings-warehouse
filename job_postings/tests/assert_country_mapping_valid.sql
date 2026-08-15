select
    l.country_code,
    l.country_name
from {{ ref('dim_location') }} as l
left join {{ ref('country_codes') }} as cc
    on
        l.country_code = cc.country_code
        and l.country_name = cc.country_name
where
    l.country_code is not null
    and cc.country_code is null
