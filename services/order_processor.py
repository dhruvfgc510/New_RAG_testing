"""
Order processing service for checkout workflow.

This service orchestrates the order processing workflow including:
- Order validation
- Inventory management
- Payment coordination
- Order state management
- Error recovery

This file depends on multiple main branch services and models.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

# ============================================
# CRITICAL DEPENDENCIES FROM MAIN BRANCH
# ============================================

from utils.database import (
    save_order,
    update_order_status,
    get_user_by_id,
)

from utils.logger import (
    log_info,
    log_error,
    log_warning,
)

from services.inventory_service import (
    reserve_stock,
    release_stock,
    confirm_reservation,
)

from services.payment_processor import (
    process_payment,
    verify_payment_status,
    PaymentStatus,
)

from models.order import Order, OrderItem, OrderStatus
from models.user import User
from models.product import Product

from config.settings import TAX_RATE, MAX_ORDER_AMOUNT


# ============================================
# ORDER PROCESSOR EXCEPTIONS
# ============================================

class OrderProcessingError(Exception):
    """Base exception for order processing errors."""
    pass


class OrderValidationError(OrderProcessingError):
    """Exception for order validation errors."""
    pass


class OrderStateError(OrderProcessingError):
    """Exception for invalid order state transitions."""
    pass


# ============================================
# ORDER PROCESSOR CLASS
# ============================================

class OrderProcessor:
    """
    Order processing orchestrator.
    
    This class coordinates the complex workflow of:
    1. Order validation
    2. Stock reservation
    3. Payment processing
    4. Order creation
    5. Error recovery
    
    Attributes:
        order_data: Order information
        user_id: User identifier
        reservations: List of stock reservations
        payment_result: Payment processing result
    """
    
    def __init__(self, user_id: str, order_data: Dict[str, any]):
        """
        Initialize order processor.
        
        Args:
            user_id: User identifier
            order_data: Order data dictionary
        """
        self.user_id = user_id
        self.order_data = order_data
        self.reservations = []
        self.payment_result = None
        self.order_id = None
    
    async def process(self) -> Dict[str, any]:
        """
        Process order through complete workflow.
        
        Returns:
            Dictionary with order processing result
            
        Raises:
            OrderProcessingError: If processing fails
        """
        try:
            # Step 1: Validate order
            await self._validate_order()
            
            # Step 2: Reserve inventory
            await self._reserve_inventory()
            
            # Step 3: Process payment
            await self._process_payment()
            
            # Step 4: Create order
            await self._create_order()
            
            # Step 5: Confirm reservations
            await self._confirm_reservations()
            
            return {
                'status': 'success',
                'order_id': self.order_id,
                'payment_transaction_id': self.payment_result['transaction_id'],
            }
        
        except Exception as e:
            await self._handle_error(e)
            raise
    
    async def _validate_order(self):
        """
        Validate order data.
        
        Uses User model and database utilities from main branch.
        """
        log_info(
            message=f"Validating order for user {self.user_id}",
            extra={'user_id': self.user_id}
        )
        
        # Validate user exists
        user = await get_user_by_id(self.user_id)
        if not user:
            raise OrderValidationError(f"User not found: {self.user_id}")
        
        # Validate order data structure
        required_fields = ['items', 'total_amount', 'shipping_address']
        missing_fields = [f for f in required_fields if f not in self.order_data]
        
        if missing_fields:
            raise OrderValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate order amount
        if self.order_data['total_amount'] > MAX_ORDER_AMOUNT:
            raise OrderValidationError(
                f"Order amount ${self.order_data['total_amount']:.2f} exceeds maximum ${MAX_ORDER_AMOUNT:.2f}"
            )
    
    async def _reserve_inventory(self):
        """
        Reserve inventory for order items.
        
        Uses inventory service from main branch.
        """
        log_info(
            message=f"Reserving inventory for {len(self.order_data['items'])} items",
            extra={'user_id': self.user_id}
        )
        
        for item in self.order_data['items']:
            reservation = await reserve_stock(
                product_id=item['product_id'],
                quantity=item['quantity'],
                order_id=f"order_{self.user_id}",
            )
            self.reservations.append(reservation['reservation_id'])
        
        log_info(
            message=f"Reserved {len(self.reservations)} items",
            extra={'reservations': self.reservations}
        )
    
    async def _process_payment(self):
        """
        Process payment for order.
        
        Uses payment processor from main branch with retry logic.
        """
        log_info(
            message=f"Processing payment for order",
            extra={'user_id': self.user_id, 'amount': self.order_data['total_amount']}
        )
        
        # Process payment using payment processor from main branch
        # This uses the retry logic and timeout handling from payment_processor.py
        self.payment_result = await process_payment(
            amount=self.order_data['total_amount'],
            card_data=self.order_data['payment_details'],
            order_id=f"order_{self.user_id}",
            user_id=self.user_id,
        )
        
        if self.payment_result['status'] != PaymentStatus.COMPLETED.value:
            raise OrderProcessingError(f"Payment failed: {self.payment_result.get('error')}")
        
        log_info(
            message="Payment processed successfully",
            extra={'transaction_id': self.payment_result['transaction_id']}
        )
    
    async def _create_order(self):
        """
        Create order in database.
        
        Uses Order model and database utilities from main branch.
        """
        order_data = {
            **self.order_data,
            'user_id': self.user_id,
            'payment_transaction_id': self.payment_result['transaction_id'],
            'payment_status': 'completed',
        }
        
        self.order_id = await save_order(order_data)
        
        log_info(
            message=f"Order created: {self.order_id}",
            extra={'order_id': self.order_id}
        )
    
    async def _confirm_reservations(self):
        """
        Confirm all stock reservations.
        
        Uses inventory service from main branch.
        """
        for reservation_id in self.reservations:
            await confirm_reservation(reservation_id)
        
        log_info(
            message=f"Confirmed {len(self.reservations)} reservations",
            extra={'order_id': self.order_id}
        )
    
    async def _handle_error(self, error: Exception):
        """
        Handle processing error and cleanup.
        
        Args:
            error: Exception that occurred
        """
        log_error(
            error_message=f"Order processing failed: {str(error)}",
            error_type=type(error).__name__,
            extra={'user_id': self.user_id}
        )
        
        # Release reservations
        if self.reservations:
            log_info(
                message=f"Releasing {len(self.reservations)} reservations due to error",
                extra={'user_id': self.user_id}
            )
            
            for reservation_id in self.reservations:
                try:
                    await release_stock(reservation_id=reservation_id)
                except Exception as e:
                    log_error(
                        error_message=f"Failed to release reservation: {str(e)}",
                        extra={'reservation_id': reservation_id}
                    )


# ============================================
# UTILITY FUNCTIONS
# ============================================

async def create_order_from_cart(user_id: str, cart_items: List[Dict[str, any]]) -> str:
    """
    Create order from shopping cart items.
    
    Args:
        user_id: User identifier
        cart_items: List of cart items
        
    Returns:
        Created order ID
    """
    # Calculate totals using TAX_RATE from main branch config
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    tax_amount = subtotal * TAX_RATE
    total_amount = subtotal + tax_amount
    
    order_data = {
        'items': cart_items,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
    }
    
    processor = OrderProcessor(user_id, order_data)
    result = await processor.process()
    
    return result['order_id']


async def cancel_order(order_id: str, reason: str) -> bool:
    """
    Cancel an existing order.
    
    Args:
        order_id: Order identifier
        reason: Cancellation reason
        
    Returns:
        True if cancelled successfully
    """
    # Update order status using database utilities
    success = await update_order_status(order_id, 'cancelled')
    
    log_info(
        message=f"Order cancelled: {order_id}",
        extra={'order_id': order_id, 'reason': reason}
    )
    
    return success
