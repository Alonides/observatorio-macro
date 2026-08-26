"""Operational Debt/NOK monitor v1.0.3."""

from .monitor import MODEL_VERSION, evaluate_operational
from .terminology import install_source_terminology

install_source_terminology()

__all__ = ["MODEL_VERSION", "evaluate_operational"]
