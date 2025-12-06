SELECT
    md5(concat_ws('||', movie_tmdb_id, index_in_script)) as id,
    index_in_script,
    content,
    movie_tmdb_id
FROM {{ ref('silver_script_blocks') }}
WHERE type = 'unknown'
