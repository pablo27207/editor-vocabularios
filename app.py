import os
from flask import Flask, render_template, session
from dotenv import load_dotenv
from models import db
from auth import auth_bp, setup_oauth

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key_please_change")

# Database Configuration
# Default to sqlite for local dev if no POSTGRES_URL provided, but user asked for Postgres
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/oceanvocab")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Google OAuth Config
app.config['GOOGLE_CLIENT_ID'] = os.environ.get("GOOGLE_CLIENT_ID")
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get("GOOGLE_CLIENT_SECRET")

db.init_app(app)
setup_oauth(app)
app.register_blueprint(auth_bp)
from routes_vocab import vocab_bp
app.register_blueprint(vocab_bp)
from routes_sparql import sparql_bp
app.register_blueprint(sparql_bp)
from routes_admin import admin_bp
app.register_blueprint(admin_bp)

@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = {'name': session.get('user_name'), 'role': session.get('user_role')}
    
    # Fetch vocabularies for dashboard
    from models import Vocabulary
    vocabularies = Vocabulary.query.all()
    
    return render_template('index.html', user=user, vocabularies=vocabularies)

@app.cli.command("import-rdf")
def import_rdf_command():
    """Imports all RDF files from the vocabularies/RDF directory."""
    from utils.rdf_loader import import_all_rdf
    # Adjust path as needed. Assuming 'vocabularies' is in the root of the workspace
    rdf_dir = os.path.join(app.root_path, 'vocabularies', 'RDF')
    if os.path.exists(rdf_dir):
        import_all_rdf(rdf_dir)
    else:
        print(f"Directory not found: {rdf_dir}")

@app.cli.command("init-db")
def init_db_command():
    """Creates database tables."""
    db.create_all()
    print("Initialized the database.")

if __name__ == '__main__':
    with app.app_context():
        # db.create_all() # Uncomment to auto-create tables for dev
        pass
    app.run(debug=True)
