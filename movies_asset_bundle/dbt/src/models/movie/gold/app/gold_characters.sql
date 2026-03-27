with source as (
    select
        md5(concat_ws('||', character_name, actor_tmdb_id, movie_tmdb_id)) as id,
        character_name as name,
        actor_tmdb_id,
        movie_tmdb_id,
        current_timestamp() as inserted_at
    from {{ ref('silver_character_actor_map') }}
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.id = t.id
where t.id is null
{% endif %}
