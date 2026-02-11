"""
Self-Contained Data Models and Configuration.

SCENARIO 3: No Missing Dependencies
This file is part of the PR and provides all models and config needed.
NO imports from main branch - everything is self-contained.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# ============================================
# CONFIGURATION CONSTANTS
# ============================================

# Tax rate for order calculations
TAX_RATE = 0.08  # 8% tax

# Maximum items allowed in cart
MAX_CART_ITEMS = 50

# Minimum order amount
MIN_ORDER_AMOUNT = 10.00


# ============================================
# ENUMS
# ============================================

class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================
# DATA MODELS
# ============================================

class Order:
    """
    Order data model.
    
    Self-contained model - no external dependencies.
    """
    
    def __init__(
        self,
        order_id: str,
        user_id: str,
        items: List[Dict],
        total: float,
        status: OrderStatus = OrderStatus.PENDING
    ):
        self.order_id = order_id
        self.user_id = user_id
        self.items = items
        self.total = total
        self.status = status
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert order to dictionary."""
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "items": self.items,
            "total": self.total,
            "status": self.status.value,
            "created_at": self.created_at.isoformat()
        }


class Product:
    """
    Product data model.
    
    Self-contained model - no external dependencies.
    """
    
    def __init__(
        self,
        product_id: str,
        name: str,
        price: float,
        stock: int = 0
    ):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.stock = stock
    
    def to_dict(self) -> Dict:
        """Convert product to dictionary."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "price": self.price,
            "stock": self.stock
        }


class User:
    """
    User data model.
    
    Self-contained model - no external dependencies.
    """
    
    def __init__(
        self,
        user_id: str,
        email: str,
        name: str
    ):
        self.user_id = user_id
        self.email = email
        self.name = name
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name
        }


class CartItem:
    """
    Cart item model.
    
    Self-contained model - no external dependencies.
    """
    
    def __init__(
        self,
        product_id: str,
        quantity: int,
        price: float
    ):
        self.product_id = product_id
        self.quantity = quantity
        self.price = price
        self.added_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert cart item to dictionary."""
        return {
            "product_id": self.product_id,
            "quantity": self.quantity,
            "price": self.price,
            "added_at": self.added_at.isoformat(),
            "subtotal": self.price * self.quantity
        }
