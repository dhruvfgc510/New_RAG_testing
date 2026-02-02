"""
Utility functions for the e-commerce application.

This package provides common utilities including:
- Input validation (email, credit card, address)
- Database operations (async CRUD)
- Transaction logging
"""

from .validator import validate_email, validate_credit_card, validate_address
from .database import save_order, get_user_by_id, update_inventory, get_product_by_id
from .logger import log_transaction, log_error, log_info

__all__ = [
    "validate_email",
    "validate_credit_card",
    "validate_address",
    "save_order",
    "get_user_by_id",
    "update_inventory",
    "get_product_by_id",
    "log_transaction",
    "log_error",
    "log_info",
]

__version__ = "1.0.0"
