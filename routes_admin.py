from flask import Blueprint, render_template, redirect, url_for, flash
from models import db, ChangeRequest, Term, User
from auth import admin_required, reviewer_required
from datetime import datetime
from flask import session

admin_bp = Blueprint('admin', __name__)

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
            # Update other fields...
            
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
