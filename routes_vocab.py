from flask import Blueprint, render_template, request, abort, session, jsonify
from models import db, Vocabulary, Term, ChangeRequest
from auth import login_required, editor_required
import json

vocab_bp = Blueprint('vocab', __name__)

@vocab_bp.route('/vocab/<int:vocab_id>')
def view_vocab(vocab_id):
    vocab = Vocabulary.query.get_or_404(vocab_id)
    terms = Term.query.filter_by(vocab_id=vocab_id).order_by(Term.concept_id).all()
    
    # Build Tree Structure
    term_map = {t.concept_id: t for t in terms}
    children_map = {t.concept_id: [] for t in terms}
    roots = []
    
    for term in terms:
        has_parent = False
        if term.broader:
            for parent_id in term.broader:
                if parent_id in term_map:
                    children_map[parent_id].append(term)
                    has_parent = True
        
        if not has_parent:
            roots.append(term)
            
    # Sort roots and children by concept_id
    roots.sort(key=lambda x: x.concept_id)
    for parent_id in children_map:
        children_map[parent_id].sort(key=lambda x: x.concept_id)
    
    user_role = session.get('user_role', 'viewer')
    
    return render_template('vocab_editor.html', vocab=vocab, terms=terms, roots=roots, children_map=children_map, user_role=user_role)

@vocab_bp.route('/term/<int:term_id>/edit', methods=['GET'])
@login_required
def edit_term_form(term_id):
    term = Term.query.get_or_404(term_id)
    return render_template('partials/_edit_form.html', term=term)

@vocab_bp.route('/term/<int:term_id>/update', methods=['POST'])
@login_required
def update_term(term_id):
    term = Term.query.get_or_404(term_id)
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    # Extract data from form
    pref_label_es = request.form.get('pref_label_es')
    pref_label_en = request.form.get('pref_label_en')
    definition_es = request.form.get('definition_es')
    definition_en = request.form.get('definition_en')
    
    # Construct proposed data
    proposed_data = {
        'pref_label_es': pref_label_es,
        'pref_label_en': pref_label_en,
        'definition_es': definition_es,
        'definition_en': definition_en,
    }
    
    if user_role in ['admin', 'reviewer']:
        # Direct update
        term.pref_label_es = pref_label_es
        term.pref_label_en = pref_label_en
        term.definition_es = definition_es
        term.definition_en = definition_en
        db.session.commit()
        return render_template('partials/_term_row.html', term=term, message="Term updated successfully")
    else:
        # Create Change Request
        cr = ChangeRequest(
            user_id=user_id,
            term_id=term.id,
            vocab_id=term.vocab_id,
            change_type='update',
            proposed_data=proposed_data,
            status='pending'
        )
        db.session.add(cr)
        db.session.commit()
        return render_template('partials/_term_row.html', term=term, message="Suggestion submitted for review")

@vocab_bp.route('/term/<int:term_id>/cancel', methods=['GET'])
def cancel_edit(term_id):
    term = Term.query.get_or_404(term_id)
    return render_template('partials/_term_row.html', term=term)
