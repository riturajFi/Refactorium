"""Core data models and typed structures."""

from .proposal import Proposal
from .proposal import VALIDATION_CHECKLIST, validate_proposal

__all__ = ["Proposal", "VALIDATION_CHECKLIST", "validate_proposal"]
