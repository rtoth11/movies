with source as (
    select distinct
        actor_tmdb_id as tmdb_id,
        actor_name as name,
        current_timestamp() as inserted_at
    from {{ ref('silver_character_actor_map') }}
    where actor_tmdb_id != -1
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.tmdb_id = t.tmdb_id
where t.tmdb_id is null
{% endif %}
