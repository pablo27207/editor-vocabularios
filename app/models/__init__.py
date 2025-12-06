"""Models package - Re-exports all models for convenient importing."""
from app.extensions import db
from app.models.user import User
from app.models.vocabulary import Vocabulary, Term
from app.models.change_request import ChangeRequest

__all__ = ['db', 'User', 'Vocabulary', 'Term', 'ChangeRequest']
