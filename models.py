from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='viewer') # admin, reviewer, editor, viewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Vocabulary(db.Model):
    __tablename__ = 'vocabularies'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False) # e.g., 'QF_IODE'
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    base_uri = db.Column(db.String(200)) # For RDF export
    version = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    terms = db.relationship('Term', backref='vocabulary', lazy=True)

class Term(db.Model):
    __tablename__ = 'terms'
    id = db.Column(db.Integer, primary_key=True)
    vocab_id = db.Column(db.Integer, db.ForeignKey('vocabularies.id'), nullable=False)
    concept_id = db.Column(db.String(100), nullable=False) # e.g., 'IODE_1'
    pref_label_es = db.Column(db.String(500))
    pref_label_en = db.Column(db.String(500))
    definition_es = db.Column(db.Text)
    definition_en = db.Column(db.Text)
    alt_labels = db.Column(JSONB) # Store list of alt labels
    
    # Relationships (stored as concept_ids or URIs for simplicity in relational DB, 
    # but could be FKs if we enforce strict integrity within the same system)
    broader = db.Column(JSONB) # List of broader concept IDs
    narrower = db.Column(JSONB)
    related = db.Column(JSONB)
    exact_match = db.Column(JSONB) # For external mappings
    
    status = db.Column(db.String(20), default='approved') # approved, deprecated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChangeRequest(db.Model):
    __tablename__ = 'change_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=True) # Null if new term
    vocab_id = db.Column(db.Integer, db.ForeignKey('vocabularies.id'), nullable=False)
    
    change_type = db.Column(db.String(20), nullable=False) # create, update, delete
    proposed_data = db.Column(JSONB, nullable=False) # Snapshot of the proposed state
    
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    reviewer_comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
