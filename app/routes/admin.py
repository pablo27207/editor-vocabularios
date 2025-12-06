"""Admin routes - dashboard and change request management."""
from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from datetime import datetime
from app.models import db, ChangeRequest, Term, User
from app.routes.auth import reviewer_required, admin_required

admin_bp = Blueprint('admin', __name__)

VALID_ROLES = ['viewer', 'editor', 'reviewer', 'admin']


@admin_bp.route('/admin')
@reviewer_required
def dashboard():
    pending_requests = ChangeRequest.query.filter_by(status='pending').order_by(ChangeRequest.created_at.desc()).all()
    return render_template('admin.html', requests=pending_requests)


@admin_bp.route('/admin/request/<int:req_id>/approve', methods=['POST'])
@reviewer_required
def approve_request(req_id):
    req = ChangeRequest.query.get_or_404(req_id)
    
    if req.change_type == 'update':
        term = Term.query.get(req.term_id)
        if term:
            data = req.proposed_data
            term.pref_label_es = data.get('pref_label_es')
            term.pref_label_en = data.get('pref_label_en')
            term.definition_es = data.get('definition_es')
            term.definition_en = data.get('definition_en')
            
            req.status = 'approved'
            req.reviewed_at = datetime.utcnow()
            req.reviewed_by = session.get('user_id')
            db.session.commit()
            
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/request/<int:req_id>/reject', methods=['POST'])
@reviewer_required
def reject_request(req_id):
    req = ChangeRequest.query.get_or_404(req_id)
    req.status = 'rejected'
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = session.get('user_id')
    db.session.commit()
    return redirect(url_for('admin.dashboard'))


# ==================== USER MANAGEMENT ====================

@admin_bp.route('/admin/users')
@admin_required
def users_list():
    """List all users for admin management."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users, valid_roles=VALID_ROLES)


@admin_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@admin_required
def update_user_role(user_id):
    """Update a user's role."""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    # Prevent admin from demoting themselves
    if user.id == session.get('user_id'):
        flash('No puedes cambiar tu propio rol.')
        return redirect(url_for('admin.users_list'))
    
    if new_role not in VALID_ROLES:
        flash('Rol inválido.')
        return redirect(url_for('admin.users_list'))
    
    user.role = new_role
    db.session.commit()
    flash(f'Rol de {user.email} actualizado a {new_role}.')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/admin/users/create', methods=['POST'])
@admin_required
def create_user():
    """Create a new user from admin panel."""
    from werkzeug.security import generate_password_hash
    
    email = request.form.get('email')
    name = request.form.get('name')
    last_name = request.form.get('last_name')
    organization = request.form.get('organization')
    password = request.form.get('password')
    role = request.form.get('role', 'viewer')
    
    # Validations
    if not email or not name or not password:
        flash('Email, nombre y contraseña son requeridos.')
        return redirect(url_for('admin.users_list'))
    
    if User.query.filter_by(email=email).first():
        flash(f'El email {email} ya está registrado.')
        return redirect(url_for('admin.users_list'))
    
    if role not in VALID_ROLES:
        role = 'viewer'
    
    user = User(
        email=email,
        name=name,
        last_name=last_name,
        organization=organization,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    flash(f'Usuario {email} creado con rol {role}.')
    return redirect(url_for('admin.users_list'))

