"""
Simplified Checkout API endpoint for e-commerce application.

SCENARIO 2: Partial/Mixed Dependencies
- Imports order_processor.py from PR (INTERNAL)
- Imports multiple files from main branch (EXTERNAL)

This demonstrates a realistic scenario where new code depends on:
1. Other new code in the PR (internal dependencies)
2. Existing infrastructure in main branch (external dependencies)
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

# ============================================
# INTERNAL DEPENDENCY (FROM PR)
# ============================================
from services.order_processor import OrderProcessor

# ============================================
# EXTERNAL DEPENDENCIES (FROM MAIN BRANCH)
# ============================================

# Validation utilities
from utils.validator import (
    validate_email,
    validate_credit_card,
    validate_address,
)

# Logging utilities
from utils.logger import (
    log_info,
    log_error,
)

# Data models
from models.order import Order, OrderStatus
from models.user import User

# Configuration
from config.settings import TAX_RATE


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
        shipping_address: Dict,
        payment_details: Dict
    ):
        self.user_id = user_id
        self.items = items
        self.email = email
        self.shipping_address = shipping_address
        self.payment_details = payment_details


async def process_checkout(request: CheckoutRequest) -> Dict:
    """
    Process checkout request.
    
    This function demonstrates MIXED dependencies:
    - Uses OrderProcessor from services/order_processor.py (INTERNAL - in PR)
    - Uses validators from utils.validator (EXTERNAL - in main branch)
    - Uses logger from utils.logger (EXTERNAL - in main branch)
    - Uses models from models.order (EXTERNAL - in main branch)
    - Uses TAX_RATE from config.settings (EXTERNAL - in main branch)
    
    Without the external files, LLM won't understand:
    - How email/card/address validation works
    - How logging is structured
    - Order model structure
    - Tax rate value
    
    Args:
        request: Checkout request data
    
    Returns:
        Dict with order details
    
    Raises:
        CheckoutError: If checkout fails
    """
    transaction_id = f"checkout_{uuid4().hex[:8]}"
    
    log_info(
        message=f"Processing checkout for user {request.user_id}",
        transaction_id=transaction_id
    )
    
    try:
        # Step 1: Validate email (uses utils.validator from main branch)
        is_valid_email, email_error = validate_email(request.email)
        if not is_valid_email:
            raise CheckoutError(f"Invalid email: {email_error}")
        
        # Step 2: Validate shipping address (uses utils.validator from main branch)
        is_valid_address, address_error = validate_address(request.shipping_address)
        if not is_valid_address:
            raise CheckoutError(f"Invalid address: {address_error}")
        
        # Step 3: Validate payment card (uses utils.validator from main branch)
        is_valid_card, card_error = validate_credit_card(
            request.payment_details.get("card_number", "")
        )
        if not is_valid_card:
            raise CheckoutError(f"Invalid card: {card_error}")
        
        # Step 4: Calculate totals
        subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in request.items)
        
        # Uses TAX_RATE from config.settings (main branch)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)
        
        # Step 5: Prepare order data
        order_data = {
            "user_id": request.user_id,
            "items": request.items,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "email": request.email,
            "shipping_address": request.shipping_address,
        }
        
        # Step 6: Process order using OrderProcessor from PR (INTERNAL DEPENDENCY)
        # This is the key internal dependency - checkout depends on order_processor
        processor = OrderProcessor(
            user_id=request.user_id,
            order_data=order_data
        )
        
        result = await processor.process()
        
        log_info(
            message=f"Checkout completed successfully",
            transaction_id=transaction_id,
            order_id=result.get("order_id")
        )
        
        return {
            "success": True,
            "order_id": result.get("order_id"),
            "total": total,
            "status": "completed"
        }
    
    except CheckoutError as e:
        log_error(
            message=f"Checkout failed: {str(e)}",
            transaction_id=transaction_id
        )
        raise
    
    except Exception as e:
        log_error(
            message=f"Unexpected checkout error: {str(e)}",
            transaction_id=transaction_id
        )
        raise CheckoutError(f"Checkout failed: {str(e)}")


async def validate_checkout_request(request: CheckoutRequest) -> bool:
    """
    Validate checkout request has all required fields.
    
    Uses validators from utils.validator (main branch).
    """
    if not request.user_id:
        raise CheckoutError("User ID required")
    
    if not request.items or len(request.items) == 0:
        raise CheckoutError("Cart is empty")
    
    if not request.email:
        raise CheckoutError("Email required")
    
    # Validate email format (uses utils.validator from main branch)
    is_valid, error = validate_email(request.email)
    if not is_valid:
        raise CheckoutError(f"Invalid email: {error}")
    
    return True


async def calculate_order_summary(items: List[Dict]) -> Dict:
    """
    Calculate order summary with tax.
    
    Uses TAX_RATE from config.settings (main branch).
    """
    subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    
    # Uses TAX_RATE from config.settings (main branch)
    # Without this file, LLM won't know the tax rate value
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)
    
    return {
        "subtotal": subtotal,
        "tax": tax,
        "tax_rate": TAX_RATE,
        "total": total,
        "item_count": len(items)
    }
