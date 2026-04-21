from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    CORS(app)

    from .routes.health import health_bp
    from .routes.llm import llm_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(llm_bp)

    return app
