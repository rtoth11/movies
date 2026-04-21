{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append'
) }}

with source as (
    select
        movies.tmdb_id as movie_tmdb_id,
        cta.character as character_name,
        coalesce(cta.actor_tmdb_id, -1) as actor_tmdb_id,
        coalesce(cta.actor_name, 'Unknown') as actor_name,
        current_timestamp() as inserted_at
    from {{ source('bronze', 'bronze_json_movies') }} movies
    lateral view explode(character_to_actor) exploded as cta
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.movie_tmdb_id = t.movie_tmdb_id
  and source.actor_tmdb_id = t.actor_tmdb_id
  and source.character_name = t.character_name
where t.movie_tmdb_id is null
{% endif %}
