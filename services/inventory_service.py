"""
Inventory management service with concurrency handling.

Provides stock management with:
- Stock reservation/release
- Concurrency safety
- Low stock alerts
- Stock availability checks
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from utils.database import update_inventory, get_product_by_id
from utils.logger import log_inventory_change, log_warning, log_error


class InventoryError(Exception):
    """Base exception for inventory errors."""
    pass


class InsufficientStockError(InventoryError):
    """Exception for insufficient stock."""
    pass


class InvalidProductError(InventoryError):
    """Exception for invalid product."""
    pass


# In-memory reservation tracking (in production, this would be in database/Redis)
_reservations = {}
_reservation_lock = asyncio.Lock()


async def reserve_stock(
    product_id: str,
    quantity: int,
    order_id: str,
    reservation_timeout_minutes: int = 15
) -> Dict[str, any]:
    """
    Reserve stock for an order with timeout.
    
    Reservations automatically expire after timeout period if not confirmed.
    
    Args:
        product_id: Product identifier
        quantity: Quantity to reserve
        order_id: Order identifier
        reservation_timeout_minutes: Reservation timeout in minutes
        
    Returns:
        Dictionary containing:
            - reservation_id: Unique reservation ID
            - product_id: Product identifier
            - quantity: Reserved quantity
            - expires_at: Reservation expiration time
            
    Raises:
        InvalidProductError: If product not found
        InsufficientStockError: If insufficient stock available
        ValueError: If invalid parameters
        
    Examples:
        >>> reservation = await reserve_stock("prod_123", 2, "order_456")
        >>> print(reservation['reservation_id'])
    """
    # Validate parameters
    if not product_id or not isinstance(product_id, str):
        raise ValueError("Product ID must be a non-empty string")
    
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    
    if quantity > 1000:
        raise ValueError("Quantity exceeds maximum limit (1000)")
    
    # Get product details
    product = await get_product_by_id(product_id)
    if not product:
        raise InvalidProductError(f"Product not found: {product_id}")
    
    async with _reservation_lock:
        # Check available stock
        available_stock = await _get_available_stock(product_id)
        
        if available_stock < quantity:
            log_warning(
                message=f"Insufficient stock for product {product_id}",
                extra={
                    'product_id': product_id,
                    'requested': quantity,
                    'available': available_stock,
                    'order_id': order_id,
                }
            )
            raise InsufficientStockError(
                f"Insufficient stock for product {product_id}: "
                f"requested={quantity}, available={available_stock}"
            )
        
        # Create reservation
        reservation_id = f"res_{uuid4().hex[:12]}"
        expires_at = datetime.utcnow() + timedelta(minutes=reservation_timeout_minutes)
        
        _reservations[reservation_id] = {
            'reservation_id': reservation_id,
            'product_id': product_id,
            'quantity': quantity,
            'order_id': order_id,
            'created_at': datetime.utcnow(),
            'expires_at': expires_at,
            'status': 'active',
        }
        
        # Update inventory
        await update_inventory(product_id, -quantity)
        
        # Log inventory change
        log_inventory_change(
            product_id=product_id,
            quantity_change=-quantity,
            reason='reservation',
            order_id=order_id
        )
        
        # Schedule automatic expiration
        asyncio.create_task(
            _expire_reservation_after_timeout(
                reservation_id,
                reservation_timeout_minutes * 60
            )
        )
        
        return {
            'reservation_id': reservation_id,
            'product_id': product_id,
            'quantity': quantity,
            'expires_at': expires_at.isoformat(),
            'order_id': order_id,
        }


async def confirm_reservation(reservation_id: str) -> bool:
    """
    Confirm stock reservation (prevents auto-expiration).
    
    Args:
        reservation_id: Reservation identifier
        
    Returns:
        True if confirmed successfully
        
    Raises:
        InventoryError: If reservation not found or already expired
    """
    async with _reservation_lock:
        reservation = _reservations.get(reservation_id)
        
        if not reservation:
            raise InventoryError(f"Reservation not found: {reservation_id}")
        
        if reservation['status'] != 'active':
            raise InventoryError(f"Reservation already {reservation['status']}")
        
        # Mark as confirmed
        reservation['status'] = 'confirmed'
        reservation['confirmed_at'] = datetime.utcnow()
        
        return True


async def release_stock(
    reservation_id: Optional[str] = None,
    product_id: Optional[str] = None,
    quantity: Optional[int] = None,
    order_id: Optional[str] = None
) -> bool:
    """
    Release reserved stock back to inventory.
    
    Can release by:
    - Reservation ID (preferred)
    - Product ID + quantity (manual release)
    
    Args:
        reservation_id: Reservation identifier
        product_id: Product identifier (if no reservation_id)
        quantity: Quantity to release (if no reservation_id)
        order_id: Order identifier for logging
        
    Returns:
        True if released successfully
        
    Examples:
        >>> # Release by reservation ID
        >>> await release_stock(reservation_id="res_abc123")
        >>> # Manual release
        >>> await release_stock(product_id="prod_123", quantity=2)
    """
    async with _reservation_lock:
        if reservation_id:
            # Release by reservation ID
            reservation = _reservations.get(reservation_id)
            
            if not reservation:
                log_warning(
                    message=f"Attempted to release non-existent reservation: {reservation_id}"
                )
                return False
            
            if reservation['status'] != 'active':
                # Already released or confirmed
                return False
            
            # Return stock to inventory
            await update_inventory(
                reservation['product_id'],
                reservation['quantity']
            )
            
            # Log inventory change
            log_inventory_change(
                product_id=reservation['product_id'],
                quantity_change=reservation['quantity'],
                reason='release',
                order_id=reservation['order_id']
            )
            
            # Mark reservation as released
            reservation['status'] = 'released'
            reservation['released_at'] = datetime.utcnow()
            
            return True
        
        elif product_id and quantity:
            # Manual release (no reservation)
            await update_inventory(product_id, quantity)
            
            log_inventory_change(
                product_id=product_id,
                quantity_change=quantity,
                reason='manual_release',
                order_id=order_id
            )
            
            return True
        
        else:
            raise ValueError("Must provide either reservation_id or (product_id + quantity)")


async def check_stock_availability(
    product_id: str,
    quantity: int
) -> Tuple[bool, int]:
    """
    Check if sufficient stock is available.
    
    Args:
        product_id: Product identifier
        quantity: Desired quantity
        
    Returns:
        Tuple of (is_available, available_quantity)
        
    Examples:
        >>> is_available, available = await check_stock_availability("prod_123", 5)
        >>> if is_available:
        ...     print("Stock available!")
    """
    # Get available stock (excluding reservations)
    available_stock = await _get_available_stock(product_id)
    
    is_available = available_stock >= quantity
    
    return is_available, available_stock


async def _get_available_stock(product_id: str) -> int:
    """
    Get available stock (excluding active reservations).
    
    Args:
        product_id: Product identifier
        
    Returns:
        Available stock quantity
    """
    # Get product from database
    product = await get_product_by_id(product_id)
    if not product:
        return 0
    
    # In production, this would query actual inventory
    # For simulation, assume 100 units per product
    total_stock = 100
    
    # Subtract active reservations
    reserved_quantity = sum(
        res['quantity']
        for res in _reservations.values()
        if res['product_id'] == product_id and res['status'] == 'active'
    )
    
    return max(0, total_stock - reserved_quantity)


async def _expire_reservation_after_timeout(
    reservation_id: str,
    timeout_seconds: int
):
    """
    Automatically expire reservation after timeout.
    
    Args:
        reservation_id: Reservation identifier
        timeout_seconds: Timeout in seconds
    """
    await asyncio.sleep(timeout_seconds)
    
    async with _reservation_lock:
        reservation = _reservations.get(reservation_id)
        
        if not reservation:
            return
        
        if reservation['status'] == 'active':
            # Reservation still active - expire it
            await release_stock(reservation_id=reservation_id)
            
            log_warning(
                message=f"Reservation expired: {reservation_id}",
                extra={
                    'reservation_id': reservation_id,
                    'product_id': reservation['product_id'],
                    'quantity': reservation['quantity'],
                    'order_id': reservation['order_id'],
                }
            )


async def get_low_stock_products(threshold: int = 10) -> List[Dict[str, any]]:
    """
    Get products with stock below threshold.
    
    Args:
        threshold: Low stock threshold
        
    Returns:
        List of products with low stock
    """
    # In production, this would query database
    # For simulation, return empty list
    return []
