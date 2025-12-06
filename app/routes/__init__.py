"""Routes package - Blueprint registration."""
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.vocab import vocab_bp
from app.routes.admin import admin_bp
from app.routes.sparql import sparql_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(vocab_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(sparql_bp)
