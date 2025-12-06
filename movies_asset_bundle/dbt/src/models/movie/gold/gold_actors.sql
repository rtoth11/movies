SELECT DISTINCT
    actor_tmdb_id AS tmdb_id,
    actor_name AS name
FROM {{ ref('silver_character_actor_map') }}
WHERE actor_tmdb_id IS NOT NULL
