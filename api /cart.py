"""
Simplified Shopping Cart API for e-commerce application.

SCENARIO 2: Partial/Mixed Dependencies
- Imports checkout.py from PR (INTERNAL)
- Imports multiple files from main branch (EXTERNAL)

This demonstrates how cart operations depend on:
1. Checkout API from the PR (internal)
2. Validators and models from main branch (external)
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

# ============================================
# INTERNAL DEPENDENCY (FROM PR)
# ============================================
from api.checkout import calculate_order_summary

# ============================================
# EXTERNAL DEPENDENCIES (FROM MAIN BRANCH)
# ============================================

# Validation utilities
from utils.validator import validate_email

# Logging utilities
from utils.logger import log_info, log_error

# Data models
from models.product import Product
from models.user import User

# Configuration
from config.settings import MAX_CART_ITEMS, MIN_ORDER_AMOUNT


class CartError(Exception):
    """Base exception for cart errors."""
    pass


class Cart:
    """Shopping cart model."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.items = []
        self.created_at = datetime.utcnow()


async def add_to_cart(user_id: str, product_id: str, quantity: int) -> Dict:
    """
    Add item to shopping cart.
    
    This function demonstrates MIXED dependencies:
    - Uses calculate_order_summary from api/checkout.py (INTERNAL - in PR)
    - Uses validate_email from utils.validator (EXTERNAL - in main branch)
    - Uses log_info from utils.logger (EXTERNAL - in main branch)
    - Uses Product model from models.product (EXTERNAL - in main branch)
    - Uses MAX_CART_ITEMS from config.settings (EXTERNAL - in main branch)
    
    Without the external files, LLM won't understand:
    - How email validation works
    - Product model structure
    - Cart size limits
    - How order summaries are calculated (even though it's in PR, it uses external deps)
    
    Args:
        user_id: User identifier
        product_id: Product to add
        quantity: Quantity to add
    
    Returns:
        Dict with cart details
    
    Raises:
        CartError: If operation fails
    """
    transaction_id = f"cart_add_{user_id[:8]}"
    
    log_info(
        message=f"Adding item to cart",
        transaction_id=transaction_id,
        user_id=user_id,
        product_id=product_id
    )
    
    try:
        # Validate quantity
        if quantity <= 0:
            raise CartError("Quantity must be positive")
        
        # Get or create cart
        cart = Cart(user_id=user_id)
        
        # Validate cart limits (uses MAX_CART_ITEMS from config.settings)
        if len(cart.items) >= MAX_CART_ITEMS:
            raise CartError(f"Cart cannot exceed {MAX_CART_ITEMS} items")
        
        # Add item to cart
        cart.items.append({
            "product_id": product_id,
            "quantity": quantity,
            "price": 29.99,  # Simplified - would fetch from Product model
            "added_at": datetime.utcnow().isoformat()
        })
        
        # Calculate cart summary using checkout API (INTERNAL DEPENDENCY)
        # This calls calculate_order_summary from api/checkout.py
        # Which itself uses TAX_RATE from config.settings (external)
        summary = await calculate_order_summary(cart.items)
        
        log_info(
            message="Item added to cart successfully",
            transaction_id=transaction_id,
            cart_total=summary["total"]
        )
        
        return {
            "success": True,
            "cart": {
                "user_id": user_id,
                "items": cart.items,
                "item_count": len(cart.items)
            },
            "summary": summary
        }
    
    except CartError as e:
        log_error(
            message=f"Failed to add to cart: {str(e)}",
            transaction_id=transaction_id
        )
        raise
    
    except Exception as e:
        log_error(
            message=f"Unexpected cart error: {str(e)}",
            transaction_id=transaction_id
        )
        raise CartError(f"Cart operation failed: {str(e)}")


async def validate_cart_for_checkout(user_id: str, email: str) -> bool:
    """
    Validate cart is ready for checkout.
    
    Uses:
    - validate_email from utils.validator (EXTERNAL)
    - MIN_ORDER_AMOUNT from config.settings (EXTERNAL)
    - calculate_order_summary from api/checkout.py (INTERNAL)
    """
    # Validate email (uses utils.validator from main branch)
    is_valid, error = validate_email(email)
    if not is_valid:
        raise CartError(f"Invalid email: {error}")
    
    # Get cart
    cart = Cart(user_id=user_id)
    
    # Check not empty
    if not cart.items:
        raise CartError("Cart is empty")
    
    # Calculate totals (uses api/checkout.py from PR - INTERNAL)
    summary = await calculate_order_summary(cart.items)
    
    # Validate minimum amount (uses config.settings from main branch - EXTERNAL)
    if summary["total"] < MIN_ORDER_AMOUNT:
        raise CartError(
            f"Order total ${summary['total']:.2f} below minimum ${MIN_ORDER_AMOUNT:.2f}"
        )
    
    return True


async def get_cart_summary(user_id: str) -> Dict:
    """
    Get cart summary with totals.
    
    Uses calculate_order_summary from api/checkout.py (INTERNAL).
    """
    cart = Cart(user_id=user_id)
    
    if not cart.items:
        return {
            "user_id": user_id,
            "items": [],
            "item_count": 0,
            "subtotal": 0,
            "tax": 0,
            "total": 0
        }
    
    # Calculate summary using checkout API (INTERNAL DEPENDENCY)
    summary = await calculate_order_summary(cart.items)
    
    return {
        "user_id": user_id,
        "items": cart.items,
        "item_count": len(cart.items),
        **summary
    }
