from flask import Blueprint, redirect, url_for, session, current_app, abort
from authlib.integrations.flask_client import OAuth
from functools import wraps
from models import db, User

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()

def setup_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        access_token_url='https://accounts.google.com/o/oauth2/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  # This is only for OpenID Connect compliant servers
        client_kwargs={'scope': 'openid email profile'},
    )

@auth_bp.route('/login')
def login():
    redirect_uri = url_for('auth.authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/authorize')
def authorize():
    token = oauth.google.authorize_access_token()
    resp = oauth.google.get('userinfo')
    user_info = resp.json()
    
    # Check if user exists, if not create (or handle as guest/pending)
    email = user_info['email']
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # For first user, maybe make admin? Or just default to viewer
        # For now, let's just create a viewer
        user = User(email=email, name=user_info.get('name'), role='viewer')
        db.session.add(user)
        db.session.commit()
    
    session['user_id'] = user.id
    session['user_role'] = user.role
    session['user_name'] = user.name
    
    return redirect('/')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    session.pop('user_name', None)
    return redirect('/')

# RBAC Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] not in roles:
                abort(403) # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return role_required(['admin'])(f)

def reviewer_required(f):
    return role_required(['admin', 'reviewer'])(f)

def editor_required(f):
    return role_required(['admin', 'reviewer', 'editor'])(f)
