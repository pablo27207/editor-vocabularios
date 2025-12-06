"""User model."""
from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))  # First Name
    last_name = db.Column(db.String(100))
    organization = db.Column(db.String(200))
    contact = db.Column(db.String(200))  # Optional contact info
    role = db.Column(db.String(20), default='viewer')  # admin, reviewer, editor, viewer
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
