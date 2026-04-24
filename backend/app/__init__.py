from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import logging
import re
from logging.handlers import RotatingFileHandler
import os

load_dotenv()

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


class StripAnsiFormatter(logging.Formatter):
    def format(self, record):
        rendered = super().format(record)
        return _ANSI_ESCAPE_RE.sub("", rendered)


def configure_logging(app):
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, level_name, logging.INFO)
    app.logger.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s [in %(pathname)s:%(lineno)d]"
    )
    file_formatter = StripAnsiFormatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s [in %(pathname)s:%(lineno)d]"
    )

    has_stream = any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, RotatingFileHandler)
        for handler in app.logger.handlers
    )
    if not has_stream:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
    else:
        for handler in app.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, RotatingFileHandler
            ):
                handler.setLevel(log_level)

    has_file = any(isinstance(handler, RotatingFileHandler) for handler in app.logger.handlers)
    if not has_file:
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, "backend.log"),
            maxBytes=1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        app.logger.addHandler(file_handler)
    else:
        for handler in app.logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                handler.setLevel(log_level)

limiter = Limiter(key_func=get_remote_address, headers_enabled=True)


def create_app():
    app = Flask(__name__)
    configure_logging(app)
    app.logger.info("Starting Prepper backend application")
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
    from .routes.chat import chat_bp
    from .routes.prompts import prompts_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(prompts_bp)

    @app.errorhandler(429)
    def rate_limit_handler(error):
        return jsonify({"error": "rate limit exceeded"}), 429

    return app
