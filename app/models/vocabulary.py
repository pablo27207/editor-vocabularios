"""Vocabulary and Term models."""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db


class Vocabulary(db.Model):
    __tablename__ = 'vocabularies'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'QF_IODE'
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    base_uri = db.Column(db.String(200))  # For RDF export
    version = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    
    status = db.Column(db.String(20), default='approved')  # approved, deprecated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
