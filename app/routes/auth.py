"""Authentication routes and decorators."""
from flask import Blueprint, redirect, url_for, session, request, render_template, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from app.models import db, User
import re

auth_bp = Blueprint('auth', __name__)


def is_valid_email(email):
    """Standard email regex validation."""
    regex = r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
    return re.search(regex, email)


def is_strong_password(password):
    """At least 8 chars, 1 uppercase, 1 number or special char."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[\d\W]", password):
        return False
    return True


# ==================== RBAC Decorators (MUST be defined before routes that use them) ====================

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
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return role_required(['admin'])(f)


def reviewer_required(f):
    return role_required(['admin', 'reviewer'])(f)


def editor_required(f):
    return role_required(['admin', 'reviewer', 'editor'])(f)


# ==================== Routes ====================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        last_name = request.form.get('last_name')
        organization = request.form.get('organization')
        contact = request.form.get('contact')
        
        error = None
        
        # Validations
        if not email or not is_valid_email(email):
            error = 'Email inválido.'
        elif not name:
            error = 'Nombre es requerido.'
        elif not last_name:
            error = 'Apellido es requerido.'
        elif not organization:
            error = 'Organización es requerida.'
        elif not password:
            error = 'Contraseña es requerida.'
        elif password != confirm_password:
            error = 'Las contraseñas no coinciden.'
        elif not is_strong_password(password):
            error = 'La contraseña debe tener al menos 8 caracteres, una mayúscula y un número o símbolo.'
        elif User.query.filter_by(email=email).first() is not None:
            error = f'El usuario {email} ya está registrado.'
            
        if error is None:
            user_count = User.query.count()
            role = 'admin' if user_count == 0 else 'viewer'
            
            user = User(
                email=email,
                name=name,
                last_name=last_name,
                organization=organization,
                contact=contact,
                password_hash=generate_password_hash(password),
                role=role
            )
            db.session.add(user)
            db.session.commit()
            flash('Cuenta creada exitosamente. Por favor inicia sesión.')
            return redirect(url_for('auth.login'))
            
        flash(error)
        
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        error = None
        
        user = User.query.filter_by(email=email).first()
        
        if user is None:
            error = 'Email incorrecto.'
        elif not user.password_hash:
            # Legacy google user without password
            error = 'Este usuario se creó con Google Auth. Login por contraseña no habilitado.'
        elif not check_password_hash(user.password_hash, password):
            error = 'Contraseña incorrecta.'
            
        if error is None:
            session.clear()
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = f"{user.name} {user.last_name or ''}".strip()
            return redirect('/')
            
        flash(error)
        
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session.get('user_id'))
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        # Update allowed fields
        user.name = request.form.get('name') or user.name
        user.last_name = request.form.get('last_name')
        user.organization = request.form.get('organization')
        user.contact = request.form.get('contact')
        
        # Update password if provided
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password:
            if new_password != confirm_password:
                flash('Las contraseñas no coinciden.')
                return render_template('auth/profile.html', user=user)
            if not is_strong_password(new_password):
                flash('La contraseña debe tener al menos 8 caracteres, una mayúscula y un número o símbolo.')
                return render_template('auth/profile.html', user=user)
            user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        session['user_name'] = f"{user.name} {user.last_name or ''}".strip()
        flash('Perfil actualizado correctamente.')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', user=user)
