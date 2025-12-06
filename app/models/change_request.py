"""ChangeRequest model."""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db


class ChangeRequest(db.Model):
    __tablename__ = 'change_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=True)  # Null if new term
    vocab_id = db.Column(db.Integer, db.ForeignKey('vocabularies.id'), nullable=False)
    
    change_type = db.Column(db.String(20), nullable=False)  # create, update, delete
    proposed_data = db.Column(JSONB, nullable=False)  # Snapshot of the proposed state
    
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewer_comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
