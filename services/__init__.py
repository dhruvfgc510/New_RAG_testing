"""
Business logic services for e-commerce application.

This package provides core business services including:
- Payment processing with gateway integration
- Email notifications
- Inventory management
"""

from .payment_processor import process_payment, refund_payment, PaymentStatus
from .email_service import send_order_confirmation, send_shipping_notification
from .inventory_service import reserve_stock, release_stock, check_stock_availability

__all__ = [
    "process_payment",
    "refund_payment",
    "PaymentStatus",
    "send_order_confirmation",
    "send_shipping_notification",
    "reserve_stock",
    "release_stock",
    "check_stock_availability",
]

__version__ = "1.0.0"
