import os

from flask import Flask
from flask_cors import CORS

from movies import SCHEMA_NAME
from movies.db import query

CREATE_SCHEMA = f"CREATE SCHEMA IF NOT EXISTS \"{SCHEMA_NAME}\""

CREATE_SEARCHES_TABLE = f"""
    CREATE TABLE IF NOT EXISTS "{SCHEMA_NAME}"."searches" (
        search_id SERIAL PRIMARY KEY,
        searched_at TIMESTAMP NOT NULL,
        query_text TEXT NOT NULL,
        type_filters TEXT,
        result_count INT NOT NULL,
        session_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
"""


def create_app():
    app = Flask(__name__)

    from movies.actors import actors_bp
    app.register_blueprint(actors_bp)

    from movies.characters import characters_bp
    app.register_blueprint(characters_bp)

    from movies.movies import movies_bp
    app.register_blueprint(movies_bp)

    CORS(app)

    @app.route("/api/health")
    def health():
        return "ok", 200

    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key")

    query(CREATE_SCHEMA)
    query(CREATE_SEARCHES_TABLE)

    return app


if __name__ == "__main__":
    app_ = create_app()
    app_.run(debug=True)
