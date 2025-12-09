"""Vocabulary routes - viewing and editing terms."""
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_babel import gettext as _
from app.models import db, Vocabulary, Term, ChangeRequest, User
from app.routes.auth import login_required

vocab_bp = Blueprint('vocab', __name__)


# ========================================
# VOCABULARY LIST AND MANAGEMENT
# ========================================

@vocab_bp.route('/vocabs')
def vocab_list():
    """List all vocabularies."""
    from sqlalchemy import func
    
    vocabularies = Vocabulary.query.order_by(Vocabulary.name).all()
    
    # Get term counts and last modified for each vocabulary
    vocab_stats = {}
    vocab_last_modified = {}
    for vocab in vocabularies:
        vocab_stats[vocab.id] = Term.query.filter_by(vocab_id=vocab.id).filter(Term.deleted_at.is_(None)).count()
        # Get the most recent updated_at from terms
        last_term = Term.query.filter_by(vocab_id=vocab.id).order_by(Term.updated_at.desc()).first()
        vocab_last_modified[vocab.id] = last_term.updated_at if last_term else vocab.created_at
    
    user_role = session.get('user_role', 'viewer')
    return render_template('vocab/list.html', vocabularies=vocabularies, vocab_stats=vocab_stats, vocab_last_modified=vocab_last_modified, user_role=user_role)


@vocab_bp.route('/vocab/new', methods=['GET'])
@login_required
def vocab_create_form():
    """Show form to create a new vocabulary."""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'reviewer', 'editor']:
        flash(_('No tienes permisos para crear vocabularios.'), 'error')
        return redirect(url_for('vocab.vocab_list'))
    users = User.query.order_by(User.name).all()
    current_user_id = session.get('user_id')
    return render_template('vocab/create.html', user_role=user_role, users=users, current_user_id=current_user_id)


@vocab_bp.route('/vocab/new', methods=['POST'])
@login_required
def vocab_create():
    """Create a new vocabulary."""
    user_role = session.get('user_role', 'viewer')
    
    if user_role not in ['admin', 'reviewer', 'editor']:
        flash(_('No tienes permisos para crear vocabularios.'), 'error')
        return redirect(url_for('vocab.vocab_list'))
    
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    name_en = request.form.get('name_en', '').strip()
    description = request.form.get('description', '').strip()
    description_en = request.form.get('description_en', '').strip()
    base_uri = request.form.get('base_uri', '').strip()
    version = request.form.get('version', '').strip()
    
    # Validation
    if not code or not name:
        flash(_('El código y nombre son obligatorios.'), 'error')
        return render_template('vocab/create.html', user_role=user_role)
    
    # Check if code already exists
    existing = Vocabulary.query.filter_by(code=code).first()
    if existing:
        flash(_('Ya existe un vocabulario con ese código.'), 'error')
        return render_template('vocab/create.html', user_role=user_role)
    
    # Get owner_id
    owner_id = request.form.get('owner_id', '').strip()
    
    # Create vocabulary
    vocab = Vocabulary(
        code=code,
        name=name,
        name_en=name_en or None,
        description=description or None,
        description_en=description_en or None,
        base_uri=base_uri or None,
        version=version or None,
        owner_id=int(owner_id) if owner_id else None
    )
    
    db.session.add(vocab)
    db.session.commit()
    
    flash(_('Vocabulario creado exitosamente.'), 'success')
    return redirect(url_for('vocab.view_vocab', vocab_id=vocab.id))


@vocab_bp.route('/vocab/<int:vocab_id>/edit', methods=['GET'])
@login_required
def vocab_edit_form(vocab_id):
    """Show form to edit vocabulary metadata."""
    vocab = Vocabulary.query.get_or_404(vocab_id)
    user_role = session.get('user_role', 'viewer')
    
    if user_role not in ['admin', 'reviewer']:
        flash(_('No tienes permisos para editar vocabularios.'), 'error')
        return redirect(url_for('vocab.view_vocab', vocab_id=vocab_id))
    
    users = User.query.order_by(User.name).all()
    return render_template('vocab/edit.html', vocab=vocab, user_role=user_role, users=users)


@vocab_bp.route('/vocab/<int:vocab_id>/edit', methods=['POST'])
@login_required
def vocab_edit(vocab_id):
    """Update vocabulary metadata."""
    vocab = Vocabulary.query.get_or_404(vocab_id)
    user_role = session.get('user_role', 'viewer')
    
    if user_role not in ['admin', 'reviewer']:
        flash(_('No tienes permisos para editar vocabularios.'), 'error')
        return redirect(url_for('vocab.view_vocab', vocab_id=vocab_id))
    
    vocab.name = request.form.get('name', vocab.name).strip()
    vocab.name_en = request.form.get('name_en', '').strip() or None
    vocab.description = request.form.get('description', '').strip() or None
    vocab.description_en = request.form.get('description_en', '').strip() or None
    vocab.base_uri = request.form.get('base_uri', '').strip() or None
    vocab.version = request.form.get('version', '').strip() or None
    owner_id = request.form.get('owner_id', '').strip()
    vocab.owner_id = int(owner_id) if owner_id else None
    
    db.session.commit()
    
    flash(_('Vocabulario actualizado exitosamente.'), 'success')
    return redirect(url_for('vocab.view_vocab', vocab_id=vocab_id))


@vocab_bp.route('/vocab/import', methods=['GET'])
@login_required
def vocab_import_form():
    """Show form to import a vocabulary from file."""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'reviewer', 'editor']:
        flash(_('No tienes permisos para importar vocabularios.'), 'error')
        return redirect(url_for('vocab.vocab_list'))
    
    # Get existing vocabularies for update option
    vocabularies = Vocabulary.query.order_by(Vocabulary.name).all()
    return render_template('vocab/import.html', vocabularies=vocabularies, user_role=user_role)


@vocab_bp.route('/vocab/import', methods=['POST'])
@login_required
def vocab_import():
    """Handle vocabulary import from file."""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'reviewer', 'editor']:
        flash(_('No tienes permisos para importar vocabularios.'), 'error')
        return redirect(url_for('vocab.vocab_list'))
    
    from app.services.import_service import (
        parse_rdf_file, detect_format, 
        create_vocabulary_from_graph, update_vocabulary_from_graph
    )
    
    # Get file
    file = request.files.get('file')
    if not file or not file.filename:
        flash(_('Por favor selecciona un archivo.'), 'error')
        return redirect(url_for('vocab.vocab_import_form'))
    
    # Detect format and parse
    format = detect_format(file.filename)
    content = file.read()
    
    try:
        # Try to decode if bytes
        if isinstance(content, bytes):
            content = content.decode('utf-8')
    except UnicodeDecodeError:
        pass  # Keep as bytes for some formats
    
    graph = parse_rdf_file(content, format)
    if not graph:
        flash(_('Error al parsear el archivo. Verifica que sea un archivo RDF válido.'), 'error')
        return redirect(url_for('vocab.vocab_import_form'))
    
    action = request.form.get('action', 'create')
    
    if action == 'update':
        vocab_id = request.form.get('vocab_id')
        if not vocab_id:
            flash(_('Por favor selecciona un vocabulario para actualizar.'), 'error')
            return redirect(url_for('vocab.vocab_import_form'))
        
        add_new = 'add_new' in request.form
        update_existing = 'update_existing' in request.form
        
        stats = update_vocabulary_from_graph(
            int(vocab_id), graph, 
            add_new=add_new, 
            update_existing=update_existing
        )
        
        if stats:
            flash(_('Vocabulario actualizado: %(added)d agregados, %(updated)d actualizados, %(skipped)d omitidos.', 
                   added=stats['added'], updated=stats['updated'], skipped=stats['skipped']), 'success')
            return redirect(url_for('vocab.view_vocab', vocab_id=vocab_id))
        else:
            flash(_('Error al actualizar el vocabulario.'), 'error')
            return redirect(url_for('vocab.vocab_import_form'))
    else:
        # Create new vocabulary
        vocab = create_vocabulary_from_graph(graph)
        if vocab:
            flash(_('Vocabulario importado exitosamente.'), 'success')
            return redirect(url_for('vocab.view_vocab', vocab_id=vocab.id))
        else:
            flash(_('Error al crear el vocabulario desde el archivo.'), 'error')
            return redirect(url_for('vocab.vocab_import_form'))


# ========================================
# TERM VIEWING AND EDITING
# ========================================


@vocab_bp.route('/vocab/<int:vocab_id>')
def view_vocab(vocab_id):
    vocab = Vocabulary.query.get_or_404(vocab_id)
    # Filter out deleted terms unless explicitly requested
    show_deleted = request.args.get('show_deleted', 'false') == 'true'
    if show_deleted:
        terms = Term.query.filter_by(vocab_id=vocab_id).order_by(Term.concept_id).all()
    else:
        terms = Term.query.filter_by(vocab_id=vocab_id).filter(Term.deleted_at.is_(None)).order_by(Term.concept_id).all()
    
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
    
    return render_template('vocab/editor.html', vocab=vocab, terms=terms, roots=roots, children_map=children_map, user_role=user_role, show_deleted=show_deleted)


@vocab_bp.route('/vocab/<int:vocab_id>/term/new')
@login_required
def term_create_form(vocab_id):
    """Show form to create a new term."""
    vocab = Vocabulary.query.get_or_404(vocab_id)
    user_role = session.get('user_role', 'viewer')
    all_terms = Term.query.filter_by(vocab_id=vocab_id).order_by(Term.concept_id).all()
    return render_template('terms/create.html', vocab=vocab, user_role=user_role, all_terms=all_terms)


@vocab_bp.route('/vocab/<int:vocab_id>/term/create', methods=['POST'])
@login_required
def create_term(vocab_id):
    """Create a new term in the vocabulary."""
    from flask import redirect, url_for, flash
    vocab = Vocabulary.query.get_or_404(vocab_id)
    user_role = session.get('user_role')
    
    concept_id = request.form.get('concept_id', '').strip()
    pref_label_es = request.form.get('pref_label_es', '').strip()
    pref_label_en = request.form.get('pref_label_en', '').strip()
    definition_es = request.form.get('definition_es', '').strip()
    definition_en = request.form.get('definition_en', '').strip()
    broader_id = request.form.get('broader', '').strip()
    
    # Validations
    if not concept_id:
        flash('El ID del concepto es requerido.')
        return redirect(url_for('vocab.term_create_form', vocab_id=vocab_id))
    
    # Check if concept_id already exists
    if Term.query.filter_by(vocab_id=vocab_id, concept_id=concept_id).first():
        flash(f'El ID "{concept_id}" ya existe en este vocabulario.')
        return redirect(url_for('vocab.term_create_form', vocab_id=vocab_id))
    
    # Create term
    term = Term(
        vocab_id=vocab_id,
        concept_id=concept_id,
        pref_label_es=pref_label_es or None,
        pref_label_en=pref_label_en or None,
        definition_es=definition_es or None,
        definition_en=definition_en or None,
        broader=[broader_id] if broader_id else None,
        status='approved' if user_role in ['admin', 'reviewer'] else 'pending'
    )
    db.session.add(term)
    db.session.commit()
    
    flash(f'Término "{concept_id}" creado.')
    return redirect(url_for('vocab.term_detail_page', term_id=term.id))


@vocab_bp.route('/term/<int:term_id>')
def term_detail_page(term_id):
    """Full page view for term details."""
    term = Term.query.get_or_404(term_id)
    vocab = Vocabulary.query.get(term.vocab_id)
    user_role = session.get('user_role', 'viewer')
    show_delete = request.args.get('action') == 'delete'
    
    # Get all terms for this vocabulary to resolve broader/narrower references
    all_terms = {t.concept_id: t for t in Term.query.filter_by(vocab_id=term.vocab_id).all()}
    
    return render_template('terms/detail.html', term=term, vocab=vocab, user_role=user_role, all_terms=all_terms, show_delete=show_delete)


@vocab_bp.route('/term/<int:term_id>/edit', methods=['GET'])
@login_required
def edit_term_form(term_id):
    """Full page edit form for a term."""
    term = Term.query.get_or_404(term_id)
    vocab = Vocabulary.query.get(term.vocab_id)
    user_role = session.get('user_role', 'viewer')
    return render_template('terms/edit.html', term=term, vocab=vocab, user_role=user_role)


@vocab_bp.route('/term/<int:term_id>/edit-full', methods=['GET'])
@login_required
def edit_term_full(term_id):
    """Return full edit form for modal display."""
    term = Term.query.get_or_404(term_id)
    vocab = Vocabulary.query.get(term.vocab_id)
    all_terms = Term.query.filter_by(vocab_id=term.vocab_id).filter(Term.id != term_id).all()
    return render_template('partials/_term_edit_modal.html', term=term, vocab=vocab, all_terms=all_terms)


@vocab_bp.route('/term/<int:term_id>/update', methods=['POST'])
@login_required
def update_term(term_id):
    from flask import redirect, url_for, flash
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
        flash('Término actualizado correctamente', 'success')
        return redirect(url_for('vocab.term_detail_page', term_id=term.id))
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
        flash('Sugerencia enviada para revisión', 'info')
        return redirect(url_for('vocab.term_detail_page', term_id=term.id))


@vocab_bp.route('/term/<int:term_id>/delete', methods=['POST'])
@login_required
def delete_term(term_id):
    """Soft delete a term with a reason."""
    from flask import redirect, url_for, flash
    term = Term.query.get_or_404(term_id)
    user_role = session.get('user_role')
    vocab_id = term.vocab_id
    
    if user_role not in ['admin', 'reviewer']:
        flash('No tienes permisos para eliminar', 'error')
        return redirect(url_for('vocab.term_detail_page', term_id=term.id))
    
    reason = request.form.get('deletion_reason', '')
    term.deleted_at = datetime.utcnow()
    term.deletion_reason = reason
    term.status = 'deleted'
    db.session.commit()
    
    flash('Término eliminado correctamente', 'success')
    return redirect(url_for('vocab.view_vocab', vocab_id=vocab_id))


@vocab_bp.route('/term/<int:term_id>/restore', methods=['POST'])
@login_required
def restore_term(term_id):
    """Restore a soft-deleted term."""
    from flask import redirect, url_for, flash
    term = Term.query.get_or_404(term_id)
    user_role = session.get('user_role')
    
    if user_role != 'admin':
        flash('Solo admins pueden restaurar', 'error')
        return redirect(url_for('vocab.term_detail_page', term_id=term.id))
    
    term.deleted_at = None
    term.deletion_reason = None
    term.status = 'approved'
    db.session.commit()
    
    flash('Término restaurado correctamente', 'success')
    return redirect(url_for('vocab.term_detail_page', term_id=term.id))


@vocab_bp.route('/term/<int:term_id>/cancel', methods=['GET'])
def cancel_edit(term_id):
    term = Term.query.get_or_404(term_id)
    user_role = session.get('user_role', 'viewer')
    return render_template('partials/_term_row.html', term=term, user_role=user_role)

