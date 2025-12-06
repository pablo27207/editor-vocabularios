"""
OceanVocab Editor - Application Factory
"""
import os
from flask import Flask, request
from dotenv import load_dotenv

from app.extensions import db, babel
from app.routes import register_blueprints
from config.settings import config


def get_locale():
    """Determine the best locale for the user."""
    lang = request.cookies.get('babel_translation')
    if lang:
        return lang
    return request.accept_languages.best_match(['es', 'en'])


def create_app(config_name=None):
    """Application Factory."""
    load_dotenv()
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))
    
    # Initialize extensions
    db.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    
    # Context processor for templates
    @app.context_processor
    def inject_conf_var():
        return dict(get_locale=get_locale)
    
    # Register blueprints
    register_blueprints(app)
    
    # CLI Commands
    register_cli_commands(app)
    
    return app


def register_cli_commands(app):
    """Register CLI commands."""
    
    @app.cli.command("init-db")
    def init_db_command():
        """Creates database tables."""
        db.create_all()
        print("Initialized the database.")
    
    @app.cli.command("import-rdf")
    def import_rdf_command():
        """Imports all RDF files from the data/RDF directory."""
        from app.services.rdf_loader import import_all_rdf
        rdf_dir = os.path.join(app.root_path, '..', 'data', 'RDF')
        if os.path.exists(rdf_dir):
            import_all_rdf(rdf_dir)
        else:
            print(f"Directory not found: {rdf_dir}")
