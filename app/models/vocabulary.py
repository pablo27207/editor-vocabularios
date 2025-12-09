"""Vocabulary and Term models."""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db


class Vocabulary(db.Model):
    __tablename__ = 'vocabularies'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'QF_IODE'
    name = db.Column(db.String(200), nullable=False)  # Name in Spanish (default)
    name_en = db.Column(db.String(200))  # Name in English
    description = db.Column(db.Text)  # Description in Spanish (default)
    description_en = db.Column(db.Text)  # Description in English
    base_uri = db.Column(db.String(200))  # For RDF export
    version = db.Column(db.String(20))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    owner = db.relationship('User', backref='owned_vocabularies')
    
    terms = db.relationship('Term', backref='vocabulary', lazy=True)


class Term(db.Model):
    __tablename__ = 'terms'
    
    id = db.Column(db.Integer, primary_key=True)
    vocab_id = db.Column(db.Integer, db.ForeignKey('vocabularies.id'), nullable=False)
    concept_id = db.Column(db.String(100), nullable=False)  # e.g., 'IODE_1'
    pref_label_es = db.Column(db.String(500))
    pref_label_en = db.Column(db.String(500))
    definition_es = db.Column(db.Text)
    definition_en = db.Column(db.Text)
    alt_labels = db.Column(JSONB)  # Store list of alt labels
    
    # Relationships (stored as concept_ids or URIs)
    broader = db.Column(JSONB)  # List of broader concept IDs
    narrower = db.Column(JSONB)
    related = db.Column(JSONB)
    exact_match = db.Column(JSONB)  # For external mappings
    close_match = db.Column(JSONB)  # For close external mappings
    
    # Metadata
    source = db.Column(db.String(500))  # dc:source from RDF
    
    # Status and soft delete
    status = db.Column(db.String(20), default='approved')  # approved, deprecated, deleted
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete timestamp
    deletion_reason = db.Column(db.Text, nullable=True)  # Reason for deletion/deprecation
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

