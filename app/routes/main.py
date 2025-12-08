"""Main routes - Index, language switching."""
from flask import Blueprint, render_template, session, request, redirect, make_response

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = {'name': session.get('user_name'), 'role': session.get('user_role')}
    
    # Fetch statistics for home page
    from app.models import Vocabulary, Term, User
    stats = {
        'vocabularies': Vocabulary.query.count(),
        'concepts': Term.query.filter(Term.deleted_at.is_(None)).count(),
        'users': User.query.count()
    }
    
    return render_template('index.html', user=user, stats=stats)


@main_bp.route('/set_language/<lang>')
def set_language(lang):
    if lang not in ['es', 'en']:
        lang = 'es'
    resp = make_response(redirect(request.referrer or '/'))
    resp.set_cookie('babel_translation', lang)
    return resp
