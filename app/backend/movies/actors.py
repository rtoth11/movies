from flask import Blueprint, jsonify

from . import SCHEMA_NAME
from .db import query

actors_bp = Blueprint("actors", __name__)


@actors_bp.route("/api/actors/<int:tmdb_id>")
def actor_details(tmdb_id):
    rows = query(f'''
        SELECT
            tmdb_id,
            name
        FROM "{SCHEMA_NAME}"."gold_actors"
        WHERE tmdb_id=%s''', [tmdb_id])

    if not rows:
        return jsonify({"error": "Actor not found"}), 404

    actor = rows[0]

    roles = query(f"""
        SELECT
            m.tmdb_id,
            m.title,
            m.year,
            c.id,
            c.name
        FROM "{SCHEMA_NAME}"."gold_characters" c
        JOIN "{SCHEMA_NAME}"."silver_movies" m
            ON m.tmdb_id = c.movie_tmdb_id
        WHERE c.actor_tmdb_id=%s
        ORDER BY m.year DESC
    """, [tmdb_id])

    return jsonify({
        "actor": {"tmdb_id": actor[0], "name": actor[1]},
        "movies": [
            {
                "tmdb_id": r[0],
                "title": r[1],
                "year": r[2],
                "character": {"id": r[3], "name": r[4]}
            } for r in roles
        ]
    })
