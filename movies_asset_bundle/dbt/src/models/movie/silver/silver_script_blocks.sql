SELECT
    movies.tmdb_id AS movie_tmdb_id,
    script_block.index AS index_in_script,
    script_block.type,
    script_block.content,
    script_block.character,
    script_block.dialogue,
    script_block.suffix,
    script_block.parentheticals
FROM {{ source('bronze', 'bronze_json_movies') }} movies
LATERAL VIEW explode(script) exploded AS script_block
