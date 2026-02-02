"""
Data models for e-commerce application.

This package provides core data models including:
- User model with authentication
- Product model with inventory
- Order model with tax calculation
"""

from .user import User, UserRole
from .product import Product, ProductCategory
from .order import Order, OrderStatus, OrderItem

__all__ = [
    "User",
    "UserRole",
    "Product",
    "ProductCategory",
    "Order",
    "OrderStatus",
    "OrderItem",
]

__version__ = "1.0.0"
