SELECT
    md5(concat_ws('||', character_name, actor_tmdb_id, movie_tmdb_id)) as id,
    character_name AS name,
    actor_tmdb_id,
    movie_tmdb_id
FROM {{ ref('silver_character_actor_map') }}
