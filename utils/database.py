"""
Database operations for e-commerce application.

Provides async database operations including:
- Order management
- User management
- Product/inventory management
- Transaction handling
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4


# Simulated database (in production, this would be PostgreSQL/MongoDB)
_DATABASE = {
    'users': {},
    'products': {},
    'orders': {},
    'inventory': {},
}

# Database lock for concurrent access
_db_lock = asyncio.Lock()


async def save_order(order_data: Dict[str, Any]) -> str:
    """
    Save order to database with transaction safety.
    
    Args:
        order_data: Dictionary containing order information:
            - user_id: User ID
            - products: List of product IDs and quantities
            - total_amount: Total order amount
            - payment_status: Payment status
            - shipping_address: Shipping address
            
    Returns:
        order_id: Unique order identifier
        
    Raises:
        ValueError: If order data is invalid
        RuntimeError: If database operation fails
        
    Examples:
        >>> order = {
        ...     "user_id": "user_123",
        ...     "products": [{"product_id": "prod_1", "quantity": 2}],
        ...     "total_amount": 99.99,
        ...     "payment_status": "completed",
        ...     "shipping_address": {...}
        ... }
        >>> order_id = await save_order(order)
    """
    # Validate required fields
    required_fields = ['user_id', 'products', 'total_amount', 'payment_status']
    missing_fields = [field for field in required_fields if field not in order_data]
    
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate products list
    if not isinstance(order_data['products'], list) or not order_data['products']:
        raise ValueError("Products must be a non-empty list")
    
    # Validate total amount
    if order_data['total_amount'] <= 0:
        raise ValueError("Total amount must be positive")
    
    async with _db_lock:
        # Generate unique order ID
        order_id = f"order_{uuid4().hex[:12]}"
        
        # Add metadata
        order_record = {
            **order_data,
            'order_id': order_id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'status': 'pending',
        }
        
        # Simulate database write delay
        await asyncio.sleep(0.01)
        
        # Save to database
        _DATABASE['orders'][order_id] = order_record
        
        return order_id


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user information from database.
    
    Args:
        user_id: Unique user identifier
        
    Returns:
        User data dictionary or None if not found
        
    Examples:
        >>> user = await get_user_by_id("user_123")
        >>> print(user['email'])
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("User ID must be a non-empty string")
    
    async with _db_lock:
        # Simulate database read delay
        await asyncio.sleep(0.005)
        
        user = _DATABASE['users'].get(user_id)
        
        if user:
            # Return copy to prevent external modifications
            return user.copy()
        
        return None


async def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve product information from database.
    
    Args:
        product_id: Unique product identifier
        
    Returns:
        Product data dictionary or None if not found
        
    Examples:
        >>> product = await get_product_by_id("prod_123")
        >>> print(product['name'], product['price'])
    """
    if not product_id or not isinstance(product_id, str):
        raise ValueError("Product ID must be a non-empty string")
    
    async with _db_lock:
        # Simulate database read delay
        await asyncio.sleep(0.005)
        
        product = _DATABASE['products'].get(product_id)
        
        if product:
            return product.copy()
        
        return None


async def update_inventory(product_id: str, quantity_change: int) -> bool:
    """
    Update product inventory with concurrency safety.
    
    Args:
        product_id: Product identifier
        quantity_change: Quantity to add (positive) or remove (negative)
        
    Returns:
        True if update successful, False otherwise
        
    Raises:
        ValueError: If invalid parameters
        RuntimeError: If insufficient inventory
        
    Examples:
        >>> # Reserve 2 items
        >>> success = await update_inventory("prod_123", -2)
        >>> # Restock 10 items
        >>> success = await update_inventory("prod_123", 10)
    """
    if not product_id or not isinstance(product_id, str):
        raise ValueError("Product ID must be a non-empty string")
    
    if not isinstance(quantity_change, int):
        raise ValueError("Quantity change must be an integer")
    
    async with _db_lock:
        # Get current inventory
        inventory = _DATABASE['inventory'].get(product_id, {'quantity': 0})
        current_quantity = inventory['quantity']
        
        # Calculate new quantity
        new_quantity = current_quantity + quantity_change
        
        # Validate inventory availability
        if new_quantity < 0:
            raise RuntimeError(
                f"Insufficient inventory for product {product_id}: "
                f"available={current_quantity}, requested={abs(quantity_change)}"
            )
        
        # Simulate database write delay
        await asyncio.sleep(0.01)
        
        # Update inventory
        _DATABASE['inventory'][product_id] = {
            'product_id': product_id,
            'quantity': new_quantity,
            'updated_at': datetime.utcnow().isoformat(),
        }
        
        return True


async def get_orders_by_user(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve user's order history.
    
    Args:
        user_id: User identifier
        limit: Maximum number of orders to return
        
    Returns:
        List of order dictionaries, sorted by creation date (newest first)
        
    Examples:
        >>> orders = await get_orders_by_user("user_123", limit=5)
        >>> for order in orders:
        ...     print(order['order_id'], order['total_amount'])
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("User ID must be a non-empty string")
    
    if limit <= 0 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    async with _db_lock:
        # Simulate database query delay
        await asyncio.sleep(0.02)
        
        # Filter orders by user_id
        user_orders = [
            order for order in _DATABASE['orders'].values()
            if order['user_id'] == user_id
        ]
        
        # Sort by creation date (newest first)
        user_orders.sort(
            key=lambda x: x['created_at'],
            reverse=True
        )
        
        # Apply limit
        return user_orders[:limit]


async def update_order_status(order_id: str, status: str) -> bool:
    """
    Update order status.
    
    Args:
        order_id: Order identifier
        status: New status (pending, processing, shipped, delivered, cancelled)
        
    Returns:
        True if update successful
        
    Raises:
        ValueError: If order not found or invalid status
    """
    valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
    
    async with _db_lock:
        order = _DATABASE['orders'].get(order_id)
        
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        # Simulate database write delay
        await asyncio.sleep(0.01)
        
        # Update order status
        order['status'] = status
        order['updated_at'] = datetime.utcnow().isoformat()
        
        return True


# Helper functions for database initialization (testing purposes)

async def initialize_test_data():
    """Initialize database with test data."""
    # Add test users
    _DATABASE['users']['user_123'] = {
        'user_id': 'user_123',
        'email': 'john@example.com',
        'name': 'John Doe',
        'created_at': '2024-01-01T00:00:00',
    }
    
    # Add test products
    _DATABASE['products']['prod_1'] = {
        'product_id': 'prod_1',
        'name': 'Laptop',
        'price': 999.99,
        'category': 'Electronics',
    }
    
    # Add test inventory
    _DATABASE['inventory']['prod_1'] = {
        'product_id': 'prod_1',
        'quantity': 50,
        'updated_at': datetime.utcnow().isoformat(),
    }


async def clear_database():
    """Clear all database tables (for testing)."""
    async with _db_lock:
        _DATABASE['users'].clear()
        _DATABASE['products'].clear()
        _DATABASE['orders'].clear()
        _DATABASE['inventory'].clear()
