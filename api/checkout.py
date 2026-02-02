"""
Checkout API endpoint for e-commerce application.

This module provides the checkout functionality with:
- Input validation (email, address, payment details)
- Payment processing with retry logic
- Inventory reservation and management
- Order creation with tax calculation
- Email notifications
- Comprehensive error handling

This file heavily depends on utilities, services, and models from the main branch.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

# ============================================
# CRITICAL DEPENDENCIES FROM MAIN BRANCH
# These imports are essential for the checkout flow
# Without these files, the LLM cannot understand the complete logic
# ============================================

# Validation utilities - Required for input validation
from utils.validator import (
    validate_email,
    validate_credit_card,
    validate_address,
    validate_phone_number,
)

# Database operations - Required for saving orders and retrieving data
from utils.database import (
    save_order,
    get_user_by_id,
    get_product_by_id,
    update_order_status,
)

# Logging utilities - Required for transaction tracking
from utils.logger import (
    log_transaction,
    log_error,
    log_info,
    log_warning,
)

# Payment processing - Required for payment gateway integration
from services.payment_processor import (
    process_payment,
    PaymentStatus,
    PaymentError,
    InsufficientFundsError,
    InvalidCardError,
)

# Email service - Required for customer notifications
from services.email_service import (
    send_order_confirmation,
    EmailError,
)

# Inventory service - Required for stock management
from services.inventory_service import (
    reserve_stock,
    confirm_reservation,
    release_stock,
    check_stock_availability,
    InsufficientStockError,
)

# Data models - Required for order creation
from models.order import Order, OrderItem, OrderStatus
from models.user import User
from models.product import Product

# Configuration - Required for business rules
from config.settings import (
    TAX_RATE,
    MAX_ORDER_AMOUNT,
    MIN_ORDER_AMOUNT,
)


# ============================================
# CHECKOUT API EXCEPTIONS
# ============================================

class CheckoutError(Exception):
    """Base exception for checkout errors."""
    pass


class ValidationError(CheckoutError):
    """Exception for validation errors."""
    pass


class CheckoutProcessingError(CheckoutError):
    """Exception for checkout processing errors."""
    pass


# ============================================
# CHECKOUT REQUEST/RESPONSE MODELS
# ============================================

class CheckoutRequest:
    """
    Checkout request data model.
    
    Attributes:
        user_id: User identifier
        items: List of items to purchase
        shipping_address: Shipping address
        billing_address: Billing address (optional, defaults to shipping)
        payment_details: Payment card information
        email: Customer email for notifications
    """
    
    def __init__(
        self,
        user_id: str,
        items: List[Dict[str, any]],
        shipping_address: Dict[str, str],
        payment_details: Dict[str, str],
        email: str,
        billing_address: Optional[Dict[str, str]] = None
    ):
        self.user_id = user_id
        self.items = items
        self.shipping_address = shipping_address
        self.billing_address = billing_address or shipping_address
        self.payment_details = payment_details
        self.email = email


class CheckoutResponse:
    """
    Checkout response data model.
    
    Attributes:
        order_id: Created order identifier
        status: Checkout status
        total_amount: Total order amount
        payment_transaction_id: Payment transaction ID
        estimated_delivery: Estimated delivery date
    """
    
    def __init__(
        self,
        order_id: str,
        status: str,
        total_amount: float,
        payment_transaction_id: Optional[str] = None,
        estimated_delivery: Optional[str] = None
    ):
        self.order_id = order_id
        self.status = status
        self.total_amount = total_amount
        self.payment_transaction_id = payment_transaction_id
        self.estimated_delivery = estimated_delivery
    
    def to_dict(self) -> Dict[str, any]:
        """Convert response to dictionary."""
        return {
            'order_id': self.order_id,
            'status': self.status,
            'total_amount': self.total_amount,
            'payment_transaction_id': self.payment_transaction_id,
            'estimated_delivery': self.estimated_delivery,
        }


# ============================================
# MAIN CHECKOUT FUNCTION
# ============================================

async def process_checkout(request: CheckoutRequest) -> CheckoutResponse:
    """
    Process checkout with complete validation and error handling.
    
    This is the main checkout flow that orchestrates:
    1. Input validation (email, address, payment card)
    2. User verification
    3. Product availability check
    4. Stock reservation
    5. Payment processing
    6. Order creation
    7. Email notification
    
    Args:
        request: CheckoutRequest containing all checkout data
        
    Returns:
        CheckoutResponse with order details
        
    Raises:
        ValidationError: If input validation fails
        InsufficientStockError: If products out of stock
        PaymentError: If payment processing fails
        CheckoutProcessingError: If checkout fails
        
    Examples:
        >>> checkout_data = CheckoutRequest(
        ...     user_id="user_123",
        ...     items=[{"product_id": "prod_1", "quantity": 2}],
        ...     shipping_address={...},
        ...     payment_details={...},
        ...     email="user@example.com"
        ... )
        >>> response = await process_checkout(checkout_data)
        >>> print(response.order_id)
    """
    transaction_id = f"checkout_{uuid4().hex[:12]}"
    reservations = []
    
    try:
        # ============================================
        # STEP 1: VALIDATE INPUT DATA
        # Uses utilities from main branch
        # ============================================
        log_info(
            message=f"Starting checkout process for user {request.user_id}",
            transaction_id=transaction_id,
            extra={'user_id': request.user_id}
        )
        
        await _validate_checkout_request(request)
        
        # ============================================
        # STEP 2: VERIFY USER EXISTS
        # Uses database utilities from main branch
        # ============================================
        user = await get_user_by_id(request.user_id)
        if not user:
            raise ValidationError(f"User not found: {request.user_id}")
        
        if not user.get('is_active', True):
            raise ValidationError("User account is not active")
        
        # ============================================
        # STEP 3: VALIDATE AND RESERVE PRODUCTS
        # Uses inventory service from main branch
        # ============================================
        order_items, reservations = await _validate_and_reserve_products(
            request.items,
            transaction_id
        )
        
        # ============================================
        # STEP 4: CALCULATE ORDER TOTALS
        # Uses Order model from main branch (which uses TAX_RATE)
        # ============================================
        subtotal = sum(item.total_price for item in order_items)
        tax_amount = subtotal * TAX_RATE
        total_amount = subtotal + tax_amount
        
        # Validate order amount limits
        if total_amount < MIN_ORDER_AMOUNT:
            raise ValidationError(f"Order amount ${total_amount:.2f} is below minimum ${MIN_ORDER_AMOUNT:.2f}")
        
        if total_amount > MAX_ORDER_AMOUNT:
            raise ValidationError(f"Order amount ${total_amount:.2f} exceeds maximum ${MAX_ORDER_AMOUNT:.2f}")
        
        log_info(
            message=f"Order calculated: subtotal=${subtotal:.2f}, tax=${tax_amount:.2f}, total=${total_amount:.2f}",
            transaction_id=transaction_id,
            extra={
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'total_amount': total_amount,
            }
        )
        
        # ============================================
        # STEP 5: PROCESS PAYMENT
        # Uses payment processor from main branch with retry logic
        # ============================================
        payment_result = await process_payment(
            amount=total_amount,
            card_data=request.payment_details,
            order_id=transaction_id,
            user_id=request.user_id
        )
        
        if payment_result['status'] != PaymentStatus.COMPLETED.value:
            raise PaymentError(f"Payment failed: {payment_result.get('error', 'Unknown error')}")
        
        log_transaction(
            transaction_id=payment_result['transaction_id'],
            amount=total_amount,
            status='completed',
            user_id=request.user_id,
            payment_method='credit_card'
        )
        
        # ============================================
        # STEP 6: CREATE ORDER
        # Uses Order model and database utilities from main branch
        # ============================================
        order_id = await _create_order(
            user_id=request.user_id,
            items=order_items,
            total_amount=total_amount,
            shipping_address=request.shipping_address,
            payment_transaction_id=payment_result['transaction_id']
        )
        
        # ============================================
        # STEP 7: CONFIRM STOCK RESERVATIONS
        # Uses inventory service from main branch
        # ============================================
        for reservation_id in reservations:
            await confirm_reservation(reservation_id)
        
        log_info(
            message=f"Stock reservations confirmed for order {order_id}",
            transaction_id=transaction_id,
            extra={'order_id': order_id, 'reservations': reservations}
        )
        
        # ============================================
        # STEP 8: SEND ORDER CONFIRMATION EMAIL
        # Uses email service from main branch
        # ============================================
        try:
            await send_order_confirmation(
                user_email=request.email,
                order_details={
                    'order_id': order_id,
                    'products': [item.to_dict() for item in order_items],
                    'total_amount': total_amount,
                    'shipping_address': request.shipping_address,
                    'estimated_delivery': _calculate_estimated_delivery(),
                }
            )
            
            log_info(
                message=f"Order confirmation email sent to {request.email}",
                transaction_id=transaction_id,
                extra={'order_id': order_id}
            )
        
        except EmailError as e:
            # Email failure shouldn't fail the entire checkout
            log_warning(
                message=f"Failed to send confirmation email: {str(e)}",
                transaction_id=transaction_id,
                extra={'order_id': order_id, 'email': request.email}
            )
        
        # ============================================
        # STEP 9: RETURN SUCCESS RESPONSE
        # ============================================
        log_info(
            message=f"Checkout completed successfully: {order_id}",
            transaction_id=transaction_id,
            extra={
                'order_id': order_id,
                'total_amount': total_amount,
                'payment_transaction_id': payment_result['transaction_id'],
            }
        )
        
        return CheckoutResponse(
            order_id=order_id,
            status='success',
            total_amount=total_amount,
            payment_transaction_id=payment_result['transaction_id'],
            estimated_delivery=_calculate_estimated_delivery()
        )
    
    except (ValidationError, InsufficientStockError) as e:
        # Release any reserved stock
        await _release_all_reservations(reservations, transaction_id)
        
        log_error(
            error_message=f"Checkout validation failed: {str(e)}",
            error_type=type(e).__name__,
            transaction_id=transaction_id,
            extra={'user_id': request.user_id}
        )
        raise
    
    except (PaymentError, InsufficientFundsError, InvalidCardError) as e:
        # Release any reserved stock
        await _release_all_reservations(reservations, transaction_id)
        
        log_error(
            error_message=f"Payment failed: {str(e)}",
            error_type=type(e).__name__,
            transaction_id=transaction_id,
            extra={
                'user_id': request.user_id,
                'amount': total_amount if 'total_amount' in locals() else None,
            }
        )
        raise
    
    except Exception as e:
        # Release any reserved stock
        await _release_all_reservations(reservations, transaction_id)
        
        log_error(
            error_message=f"Checkout processing error: {str(e)}",
            error_type="CheckoutProcessingError",
            transaction_id=transaction_id,
            extra={'user_id': request.user_id}
        )
        raise CheckoutProcessingError(f"Checkout failed: {str(e)}")


# ============================================
# HELPER FUNCTIONS
# ============================================

async def _validate_checkout_request(request: CheckoutRequest):
    """
    Validate all checkout request data.
    
    This function uses validation utilities from main branch:
    - validate_email()
    - validate_address()
    - validate_credit_card()
    """
    # Validate email
    is_valid_email, email_error = validate_email(request.email)
    if not is_valid_email:
        raise ValidationError(f"Invalid email: {email_error}")
    
    # Validate shipping address
    is_valid_address, address_error = validate_address(request.shipping_address)
    if not is_valid_address:
        raise ValidationError(f"Invalid shipping address: {address_error}")
    
    # Validate billing address if provided
    if request.billing_address != request.shipping_address:
        is_valid_billing, billing_error = validate_address(request.billing_address)
        if not is_valid_billing:
            raise ValidationError(f"Invalid billing address: {billing_error}")
    
    # Validate payment card
    card_number = request.payment_details.get('card_number', '')
    is_valid_card, card_error = validate_credit_card(card_number)
    if not is_valid_card:
        raise ValidationError(f"Invalid credit card: {card_error}")
    
    # Validate items list
    if not request.items or not isinstance(request.items, list):
        raise ValidationError("Items list cannot be empty")
    
    for item in request.items:
        if 'product_id' not in item or 'quantity' not in item:
            raise ValidationError("Each item must have product_id and quantity")
        
        if item['quantity'] <= 0:
            raise ValidationError(f"Invalid quantity for product {item['product_id']}")


async def _validate_and_reserve_products(
    items: List[Dict[str, any]],
    transaction_id: str
) -> tuple[List[OrderItem], List[str]]:
    """
    Validate product availability and reserve stock.
    
    Uses:
    - get_product_by_id() from database utilities
    - reserve_stock() from inventory service
    """
    order_items = []
    reservations = []
    
    for item_data in items:
        product_id = item_data['product_id']
        quantity = item_data['quantity']
        
        # Get product details
        product = await get_product_by_id(product_id)
        if not product:
            raise ValidationError(f"Product not found: {product_id}")
        
        if not product.get('is_active', True):
            raise ValidationError(f"Product is not available: {product_id}")
        
        # Check stock availability
        is_available, available_qty = await check_stock_availability(product_id, quantity)
        if not is_available:
            raise InsufficientStockError(
                f"Insufficient stock for {product.get('name', product_id)}: "
                f"requested={quantity}, available={available_qty}"
            )
        
        # Reserve stock
        reservation = await reserve_stock(
            product_id=product_id,
            quantity=quantity,
            order_id=transaction_id
        )
        reservations.append(reservation['reservation_id'])
        
        # Create order item
        order_item = OrderItem(
            product_id=product_id,
            product_name=product.get('name', 'Unknown'),
            quantity=quantity,
            unit_price=product.get('price', 0.0)
        )
        order_items.append(order_item)
    
    return order_items, reservations


async def _create_order(
    user_id: str,
    items: List[OrderItem],
    total_amount: float,
    shipping_address: Dict[str, str],
    payment_transaction_id: str
) -> str:
    """
    Create order in database.
    
    Uses:
    - Order model from main branch
    - save_order() from database utilities
    """
    order_data = {
        'user_id': user_id,
        'products': [item.to_dict() for item in items],
        'total_amount': total_amount,
        'payment_status': 'completed',
        'shipping_address': shipping_address,
        'payment_transaction_id': payment_transaction_id,
    }
    
    order_id = await save_order(order_data)
    return order_id


async def _release_all_reservations(reservations: List[str], transaction_id: str):
    """Release all stock reservations (cleanup on error)."""
    if not reservations:
        return
    
    log_info(
        message=f"Releasing {len(reservations)} stock reservations",
        transaction_id=transaction_id,
        extra={'reservations': reservations}
    )
    
    for reservation_id in reservations:
        try:
            await release_stock(reservation_id=reservation_id)
        except Exception as e:
            log_error(
                error_message=f"Failed to release reservation {reservation_id}: {str(e)}",
                transaction_id=transaction_id
            )


def _calculate_estimated_delivery() -> str:
    """Calculate estimated delivery date."""
    from datetime import timedelta
    estimated = datetime.utcnow() + timedelta(days=5)
    return estimated.strftime('%Y-%m-%d')
