import datetime
import uuid

from flask import Blueprint, request, jsonify, session

from . import SCHEMA_NAME
from .db import query

movies_bp = Blueprint("movies", __name__)


@movies_bp.route("/api/movies")
def search_movies():
    q = request.args.get("q")
    types = request.args.getlist("types[]")

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    offset = (page - 1) * limit

    sql = f"""
    WITH filtered_movies AS (
        SELECT
            m.tmdb_id,
            m.title,
            m.year,
            COUNT(*) AS total_matches
        FROM "{SCHEMA_NAME}"."silver_movies" m
        JOIN "{SCHEMA_NAME}"."all_tables" at
            ON m.tmdb_id = at.movie_tmdb_id
        WHERE (
                %s IS NULL
                OR at.content ILIKE '%%' || %s || '%%'
                OR at.search_vector @@ plainto_tsquery(%s)
            )
            AND (
                %s IS NULL
                OR at.type = ANY(%s::text[])
            )
        GROUP BY m.tmdb_id, m.title, m.year
        HAVING COUNT(*) > 0
    )
    SELECT
        tmdb_id,
        title,
        year,
        total_matches,
        COUNT(*) OVER () AS total_movies
    FROM filtered_movies
    ORDER BY title
    LIMIT %s OFFSET %s;
    """

    params = [
        q, q, q,
        types if types else None,
        types if types else None,
        limit, offset
    ]

    rows = query(sql, params)

    total = rows[0][4] if rows else 0

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    session_id = session["session_id"]

    query(
        """
        INSERT INTO searches (searched_at, query_text, type_filters, result_count, session_id)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            datetime.datetime.now(),
            q,
            ",".join(types) if types else None,
            total,
            session_id
        )
    )

    return jsonify({
        "items": [
            {
                "tmdb_id": r[0],
                "title": r[1],
                "year": r[2],
                "total_matches": r[3]
            }
            for r in rows
        ],
        "total": total
    })


@movies_bp.route("/api/movies/<int:tmdb_id>")
def movie_details(tmdb_id):
    rows = query(f'''
        SELECT
            tmdb_id,
            title,
            year
        FROM "{SCHEMA_NAME}"."silver_movies"
        WHERE tmdb_id=%s''', [tmdb_id])

    if not rows:
        return jsonify({"error": "Movie not found"}), 404

    movie = rows[0]

    characters = query(f"""
        SELECT
            c.id,
            c.name,
            a.tmdb_id,
            a.name
        FROM "{SCHEMA_NAME}"."gold_characters" c
        JOIN "{SCHEMA_NAME}"."gold_actors" a
            ON a.tmdb_id = c.actor_tmdb_id
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


@movies_bp.route("/api/movies/<int:tmdb_id>/script_blocks")
def movie_script_blocks(tmdb_id):
    q = request.args.get("q")
    types = request.args.getlist("types[]")

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    offset = (page - 1) * limit

    sql = f"""
    SELECT
        at.type,
        at.content,
        at.character_id,
        at.character,
        COUNT(*) OVER() AS total_count
    FROM "{SCHEMA_NAME}"."all_tables" at
    WHERE at.movie_tmdb_id = %s
        AND (
            %s IS NULL
            OR at.content ILIKE '%%' || %s || '%%'
            OR at.search_vector @@ plainto_tsquery(%s)
        )
        AND (
            %s IS NULL
            OR at.type = ANY(%s::text[])
        )
    ORDER BY at.type
    LIMIT %s OFFSET %s;
    """

    params = [
        tmdb_id,
        q, q, q,
        types if types else None,
        types if types else None,
        limit, offset
    ]

    rows = query(sql, params)

    total = rows[0][4] if rows else 0

    return jsonify({
        "items": [
            {
                "type": r[0],
                "content": r[1],
                "character_id": r[2],
                "character": r[3]
            }
            for r in rows
        ],
        "total": total
    })


@movies_bp.route("/api/movies/<int:tmdb_id>/script")
def movie_script(tmdb_id):
    rows = query(f'''
        SELECT title
        FROM "{SCHEMA_NAME}"."silver_movies"
        WHERE tmdb_id=%s
    ''', [tmdb_id])

    if not rows:
        return jsonify({"error": "Movie not found"}), 404

    movie_title = rows[0][0]

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
        block = {
            "type": r[0],
            "index_in_script": r[1],
        }

        if r[0] in ("scene", "description", "unknown"):
            block["text"] = r[3]

        elif r[0] in ("dialogue", "empty_dialogue"):
            block["character"] = r[2]
            block["suffix"] = r[4]
            block["parentheticals"] = r[5]
            block["text"] = r[3] or "<DIALOGUE MISSING>"

        else:
            block["text"] = r[3]

        block["text"] = block["text"].replace("\n", " ").replace("  ", " ").strip()

        blocks.append(block)

    return jsonify({
        "tmdb_id": tmdb_id,
        "movie_title": movie_title,
        "blocks": blocks
    })
