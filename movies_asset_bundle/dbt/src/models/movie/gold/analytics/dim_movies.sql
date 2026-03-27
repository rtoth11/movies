with source as (
    select
        tmdb_id,
        title,
        year
    from {{ ref('silver_movies') }}
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
    on source.tmdb_id = t.tmdb_id
where t.tmdb_id is null
{% endif %}
