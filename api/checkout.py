"""
Self-Contained Checkout API endpoint.

SCENARIO 3: No Missing Dependencies
- ALL imports are from PR files (INTERNAL only)
- NO imports from main branch (EXTERNAL)

This demonstrates a fully self-contained feature with all utilities included.
"""

import asyncio
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

# ============================================
# ALL INTERNAL DEPENDENCIES (FROM PR)
# ============================================
from services.order_processor import OrderProcessor
from utils import validate_email, validate_address, log_info, log_error
from models import Order, TAX_RATE


class CheckoutError(Exception):
    """Base exception for checkout errors."""
    pass


class CheckoutRequest:
    """Checkout request model."""
    
    def __init__(
        self,
        user_id: str,
        items: List[Dict],
        email: str,
        shipping_address: Dict
    ):
        self.user_id = user_id
        self.items = items
        self.email = email
        self.shipping_address = shipping_address


async def process_checkout(request: CheckoutRequest) -> Dict:
    """
    Process checkout request.
    
    This function uses ONLY internal dependencies:
    - OrderProcessor from services/order_processor.py (INTERNAL - in PR)
    - Validators from utils.py (INTERNAL - in PR)
    - Logger from utils.py (INTERNAL - in PR)
    - TAX_RATE from models.py (INTERNAL - in PR)
    
    Everything the LLM needs is in the PR - no missing context!
    
    Args:
        request: Checkout request data
    
    Returns:
        Dict with order details
    
    Raises:
        CheckoutError: If checkout fails
    """
    transaction_id = f"checkout_{uuid4().hex[:8]}"
    
    log_info(f"Processing checkout for user {request.user_id}", transaction_id)
    
    try:
        # Step 1: Validate email (uses utils.py from PR)
        if not validate_email(request.email):
            raise CheckoutError("Invalid email address")
        
        # Step 2: Validate shipping address (uses utils.py from PR)
        if not validate_address(request.shipping_address):
            raise CheckoutError("Invalid shipping address")
        
        # Step 3: Calculate totals
        subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in request.items)
        
        # Uses TAX_RATE from models.py (PR)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)
        
        # Step 4: Prepare order data
        order_data = {
            "user_id": request.user_id,
            "items": request.items,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "email": request.email,
            "shipping_address": request.shipping_address,
        }
        
        # Step 5: Process order using OrderProcessor from PR (INTERNAL)
        processor = OrderProcessor(user_id=request.user_id, order_data=order_data)
        result = await processor.process()
        
        log_info(f"Checkout completed", transaction_id)
        
        return {
            "success": True,
            "order_id": result.get("order_id"),
            "total": total,
            "status": "completed"
        }
    
    except CheckoutError as e:
        log_error(f"Checkout failed: {str(e)}", transaction_id)
        raise
    
    except Exception as e:
        log_error(f"Unexpected error: {str(e)}", transaction_id)
        raise CheckoutError(f"Checkout failed: {str(e)}")


async def calculate_order_summary(items: List[Dict]) -> Dict:
    """
    Calculate order summary with tax.
    
    Uses TAX_RATE from models.py (INTERNAL - in PR).
    """
    subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)
    
    return {
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "item_count": len(items)
    }
