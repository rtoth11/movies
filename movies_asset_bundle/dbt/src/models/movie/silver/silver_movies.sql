SELECT
    tmdb_id,
    title,
    year
FROM {{ source('bronze', 'bronze_json_movies') }}
