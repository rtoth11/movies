from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)

    from movies.actors import actors_bp
    app.register_blueprint(actors_bp)

    from movies.characters import characters_bp
    app.register_blueprint(characters_bp)

    from movies.movies import movies_bp
    app.register_blueprint(movies_bp)

    CORS(app)

    @app.route("/health")
    def health():
        return "ok", 200

    return app


if __name__ == "__main__":
    app_ = create_app()
    app_.run(debug=True)
