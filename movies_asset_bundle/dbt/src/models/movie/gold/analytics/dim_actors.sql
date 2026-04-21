with source as (
    select distinct
        actor_tmdb_id as tmdb_id,
        actor_name as name
    from {{ ref('silver_character_actor_map') }}
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
    on source.tmdb_id = t.tmdb_id
where t.tmdb_id is null
{% endif %}
