from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

limiter = Limiter(key_func=get_remote_address, headers_enabled=True)


def create_app():
    app = Flask(__name__)
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ["http://localhost:3000", "http://127.0.0.1:3000"]
            }
        },
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    limiter.init_app(app)

    from .routes.health import health_bp
    from .routes.llm import llm_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(llm_bp)

    @app.errorhandler(429)
    def rate_limit_handler(error):
        return jsonify({"error": "rate limit exceeded"}), 429

    return app
