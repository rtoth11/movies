SELECT
    md5(concat_ws('||', s.movie_tmdb_id, index_in_script)) as id,
    index_in_script,
    dialogue,
    suffix,
    parentheticals,
    s.movie_tmdb_id,
    md5(concat_ws('||', character, actor_tmdb_id, s.movie_tmdb_id)) AS character_id
FROM {{ ref('silver_script_blocks') }} s
LEFT JOIN {{ ref('silver_character_actor_map') }} c
    ON s.movie_tmdb_id = c.movie_tmdb_id
    AND s.character = c.character_name
WHERE s.type = 'dialogue'
