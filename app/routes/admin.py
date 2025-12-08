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
    return render_template('admin/dashboard.html', requests=pending_requests)


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
    return render_template('users/list.html', users=users, valid_roles=VALID_ROLES)


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


@admin_bp.route('/admin/users/new')
@admin_required
def user_create_form():
    """Show form to create a new user."""
    return render_template('users/create.html', valid_roles=VALID_ROLES)


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
        return redirect(url_for('admin.user_create_form'))
    
    if User.query.filter_by(email=email).first():
        flash(f'El email {email} ya está registrado.')
        return redirect(url_for('admin.user_create_form'))
    
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
    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/admin/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    """View user details."""
    user = User.query.get_or_404(user_id)
    current_user_id = session.get('user_id')
    return render_template('users/detail.html', user=user, current_user_id=current_user_id, valid_roles=VALID_ROLES)


@admin_bp.route('/admin/users/<int:user_id>/edit')
@admin_required
def user_edit_form(user_id):
    """Edit user form."""
    user = User.query.get_or_404(user_id)
    current_user_id = session.get('user_id')
    return render_template('users/edit.html', user=user, current_user_id=current_user_id, valid_roles=VALID_ROLES)


@admin_bp.route('/admin/users/<int:user_id>/update', methods=['POST'])
@admin_required
def update_user(user_id):
    """Update user details."""
    user = User.query.get_or_404(user_id)
    current_user_id = session.get('user_id')
    
    # Update fields
    user.name = request.form.get('name', user.name)
    user.last_name = request.form.get('last_name', user.last_name)
    user.organization = request.form.get('organization', user.organization)
    user.contact = request.form.get('contact', user.contact)
    
    # Update role (but not for self)
    new_role = request.form.get('role')
    if new_role and new_role in VALID_ROLES and user.id != current_user_id:
        user.role = new_role
    
    db.session.commit()
    flash('Usuario actualizado correctamente.')
    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    current_user_id = session.get('user_id')
    
    # Prevent admin from deleting themselves
    if user.id == current_user_id:
        flash('No puedes eliminarte a ti mismo.')
        return redirect(url_for('admin.user_detail', user_id=user.id))
    
    email = user.email
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {email} eliminado.')
    return redirect(url_for('admin.users_list'))

