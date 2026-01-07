from flask import Blueprint, jsonify

from . import SCHEMA_NAME
from .db import query

characters_bp = Blueprint("characters", __name__)


@characters_bp.route("/api/characters/<string:character_id>")
def character_details(character_id):
    rows = query(f"""
        SELECT c.name, m.tmdb_id, m.title
        FROM "{SCHEMA_NAME}"."gold_characters" c
        JOIN "{SCHEMA_NAME}"."silver_movies" m ON m.tmdb_id = c.movie_tmdb_id
        WHERE c.id=%s
    """, [character_id])

    if not rows:
        return jsonify({"error": "Character not found"}), 404

    char = rows[0]

    dialogues = query(f"""
        SELECT dialogue, index_in_script
        FROM "{SCHEMA_NAME}"."gold_dialogues"
        WHERE character_id=%s
        ORDER BY index_in_script
    """, [character_id])

    return jsonify({
        "character": {
            "name": char[0],
            "movie": {"tmdb_id": char[1], "title": char[2]}
        },
        "dialogues": [
            {"dialogue": d[0], "index": d[1]} for d in dialogues
        ]
    })
