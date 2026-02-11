"""
Self-Contained Shopping Cart API.

SCENARIO 3: No Missing Dependencies
- ALL imports are from PR files (INTERNAL only)
- NO imports from main branch (EXTERNAL)
"""

from datetime import datetime
from typing import Dict, List

# ============================================
# ALL INTERNAL DEPENDENCIES (FROM PR)
# ============================================
from api.checkout import calculate_order_summary
from utils import validate_email, log_info, log_error
from models import MAX_CART_ITEMS


class CartError(Exception):
    """Base exception for cart errors."""
    pass


class Cart:
    """Shopping cart model."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.items = []


async def add_to_cart(user_id: str, product_id: str, quantity: int) -> Dict:
    """
    Add item to shopping cart.
    
    This function uses ONLY internal dependencies:
    - calculate_order_summary from api/checkout.py (INTERNAL - in PR)
    - validate_email from utils.py (INTERNAL - in PR)
    - log_info from utils.py (INTERNAL - in PR)
    - MAX_CART_ITEMS from models.py (INTERNAL - in PR)
    
    Everything the LLM needs is in the PR!
    
    Args:
        user_id: User identifier
        product_id: Product to add
        quantity: Quantity to add
    
    Returns:
        Dict with cart details
    """
    transaction_id = f"cart_{user_id[:8]}"
    
    log_info(f"Adding item to cart", transaction_id)
    
    try:
        if quantity <= 0:
            raise CartError("Quantity must be positive")
        
        cart = Cart(user_id=user_id)
        
        # Uses MAX_CART_ITEMS from models.py (PR)
        if len(cart.items) >= MAX_CART_ITEMS:
            raise CartError(f"Cart cannot exceed {MAX_CART_ITEMS} items")
        
        cart.items.append({
            "product_id": product_id,
            "quantity": quantity,
            "price": 29.99,
            "added_at": datetime.utcnow().isoformat()
        })
        
        # Uses calculate_order_summary from api/checkout.py (PR)
        summary = await calculate_order_summary(cart.items)
        
        log_info(f"Item added to cart", transaction_id)
        
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
        log_error(f"Cart error: {str(e)}", transaction_id)
        raise


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
    
    summary = await calculate_order_summary(cart.items)
    
    return {
        "user_id": user_id,
        "items": cart.items,
        "item_count": len(cart.items),
        **summary
    }
