{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    unique_key = ['movie_tmdb_id', 'index_in_script']
) }}

with source as (
    select
        movies.tmdb_id as movie_tmdb_id,
        script_block.index as index_in_script,
        script_block.type,
        script_block.content,
        script_block.character,
        script_block.dialogue,
        script_block.suffix,
        script_block.parentheticals,
        current_timestamp() as inserted_at
    from {{ source('bronze', 'bronze_json_movies') }} movies
    lateral view explode(script) exploded as script_block
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.movie_tmdb_id = t.movie_tmdb_id
  and source.index_in_script = t.index_in_script
where t.movie_tmdb_id is null
{% endif %}
