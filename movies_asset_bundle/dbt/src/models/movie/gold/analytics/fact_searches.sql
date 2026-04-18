with source as (
    select
        search_id,
        query_text,
        type_filters,
        result_count,
        created_at,
        cast(to_char(searched_at, 'yyyyMMdd') as integer) as searched_at_date_key,
        session_id,
        cast(to_char(created_at, 'yyyyMMdd') as integer) as created_at_date_key
    from {{ ref('silver_searches') }}
)

{% if is_incremental() %}

, max_created_at as (
    select max(created_at) as max_created_at
    from {{ this }}
)

select source.*
from source
inner join max_created_at
    on source.created_at > max_created_at.max_created_at

{% else %}

select * from source

{% endif %}
