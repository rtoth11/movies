with source as (
    select
        search_id,
        timestamp_millis(searched_at) as searched_at,
        query_text,
        split(coalesce(type_filters, 'description,dialogue,scene,unknown'), ',') as type_filters,
        result_count,
        session_id,
        timestamp_millis(created_at) as created_at
    from {{ source('bronze', 'bronze_searches') }}
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
