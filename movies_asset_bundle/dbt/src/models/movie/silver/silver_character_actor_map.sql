SELECT
    movies.tmdb_id AS movie_tmdb_id,
    cta.character AS character_name,
    cta.actor_tmdb_id,
    cta.actor_name
FROM {{ source('bronze', 'bronze_json_movies') }} movies
LATERAL VIEW explode(character_to_actor) exploded AS cta
