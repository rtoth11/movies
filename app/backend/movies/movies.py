from flask import Blueprint, request, jsonify

from . import SCHEMA_NAME
from .db import query
from .utils import generate_script

movies_bp = Blueprint("movies", __name__)


@movies_bp.route("/movies")
def search_movies():
    title = request.args.get("title")
    year = request.args.get("year")
    q = request.args.get("q")
    types = request.args.getlist("types")

    sql = f"""
    SELECT
        m.tmdb_id,
        m.title,
        m.year,
        at.content,
        at.character_id,
        at.character
    FROM "{SCHEMA_NAME}"."silver_movies" m
    LEFT JOIN "{SCHEMA_NAME}"."all_tables" at
           ON at.movie_tmdb_id = m.tmdb_id
    WHERE (%s IS NULL OR m.title ILIKE %s)
      AND (%s IS NULL OR m.year = %s)
      AND (
          %s IS NULL
          OR at.content ILIKE '%%' || %s || '%%'
          OR at.search_vector @@ plainto_tsquery(%s)
      )
      AND (
          %s IS NULL
          OR at.type = ANY(%s::text[])
      )
    ORDER BY m.year DESC;
    """

    params = [
        title, f"%{title}%" if title else None,
        year, year,
        q, q, q,
        types if types else None,
        types if types else None
    ]

    rows = query(sql, params)

    return jsonify([
        {
            "tmdb_id": r[0],
             "title": r[1],
             "year": r[2],
             "content": r[3],
             "character_id": r[4],
             "character": r[5]
        }
        for r in rows
    ])


@movies_bp.route("/movies/<int:tmdb_id>")
def movie_details(tmdb_id):
    movie = query(
        f'SELECT tmdb_id, title, year FROM "{SCHEMA_NAME}"."silver_movies" WHERE tmdb_id=%s',
        [tmdb_id]
    )[0]

    characters = query(f"""
        SELECT c.id, c.name, a.tmdb_id, a.name
        FROM "{SCHEMA_NAME}"."gold_characters" c
        JOIN "{SCHEMA_NAME}"."gold_actors" a ON a.tmdb_id = c.actor_tmdb_id
        WHERE c.movie_tmdb_id=%s
        ORDER BY c.name
    """, [tmdb_id])

    return jsonify({
        "movie": {
            "tmdb_id": movie[0],
            "title": movie[1],
            "year": movie[2]
        },
        "characters": [
            {
                "id": c[0],
                "name": c[1],
                "actor": {
                    "tmdb_id": c[2],
                    "name": c[3]
                }
            } for c in characters
        ]
    })


@movies_bp.route("/movies/<int:tmdb_id>/script")
def movie_script(tmdb_id):
    rows = query(f"""
        SELECT
            type,
            index_in_script,
            character,
            content,
            suffix,
            parentheticals
        FROM "{SCHEMA_NAME}"."all_tables"
        WHERE movie_tmdb_id=%s
        ORDER BY index_in_script
    """, [tmdb_id])

    blocks = []
    for r in rows:
        blocks.append({
            "type": r[0],
            "index_in_script": r[1],
            "character": r[2],
            "content": r[3],
            "suffix": r[4],
            "parentheticals": r[5],
        })

    script = generate_script(blocks)

    return jsonify({
        "tmdb_id": tmdb_id,
        "script": script
    })
