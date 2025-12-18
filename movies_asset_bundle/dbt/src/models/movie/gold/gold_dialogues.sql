{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    unique_key = 'id'
) }}

with source as (
    select
        md5(concat_ws('||', s.movie_tmdb_id, index_in_script)) as id,
        index_in_script,
        dialogue,
        suffix,
        parentheticals,
        s.movie_tmdb_id,
        md5(concat_ws('||', character, actor_tmdb_id, s.movie_tmdb_id)) as character_id,
        current_timestamp() as inserted_at
    from {{ ref('silver_script_blocks') }} s
    left join {{ ref('silver_character_actor_map') }} c
        on s.movie_tmdb_id = c.movie_tmdb_id
        AND s.character = c.character_name
    where s.type = 'dialogue'
)

select source.*
from source

{% if is_incremental() %}
left join {{ this }} t
  on source.id = t.id
where t.id is null
{% endif %}
