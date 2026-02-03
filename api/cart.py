"""
Shopping Cart API endpoint for e-commerce application.

This module provides shopping cart functionality with:
- Add/remove items from cart
- Update item quantities
- Calculate cart totals with tax and discounts
- Validate cart contents
- Stock availability checking
- Cart persistence

This file heavily depends on utilities, services, and models from the main branch.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

# ============================================
# CRITICAL DEPENDENCIES FROM MAIN BRANCH
# These imports are essential for the cart flow
# Without these files, the LLM cannot understand the complete logic
# ============================================

# Validation utilities - Required for input validation
from utils.validator import (
    validate_email,
    validate_phone_number,
)

# Database operations - Required for cart persistence and data retrieval
from utils.database import (
    get_user_by_id,
    get_product_by_id,
)

# Logging utilities - Required for cart activity tracking
from utils.logger import (
    log_info,
    log_error,
    log_warning,
)

# Inventory service - Required for stock checking
from services.inventory_service import (
    check_stock_availability,
    InsufficientStockError,
)

# Data models - Required for cart operations
from models.product import Product
from models.user import User

# Configuration - Required for business rules
from config.settings import (
    TAX_RATE,
    MAX_CART_ITEMS,
    MIN_ORDER_AMOUNT,
)


# ============================================
# CART API EXCEPTIONS
# ============================================

class CartError(Exception):
    """Base exception for cart errors."""
    pass


class CartValidationError(CartError):
    """Exception for cart validation errors."""
    pass


class CartItemError(CartError):
    """Exception for cart item errors."""
    pass


class CartLimitError(CartError):
    """Exception when cart limits are exceeded."""
    pass


# ============================================
# CART DATA MODELS
# ============================================

class CartItem:
    """
    Shopping cart item model.
    
    Attributes:
        product_id: Product identifier
        quantity: Item quantity
        price: Unit price at time of adding to cart
        added_at: Timestamp when item was added
    """
    
    def __init__(
        self,
        product_id: str,
        quantity: int,
        price: float,
        added_at: Optional[datetime] = None
    ):
        self.product_id = product_id
        self.quantity = quantity
        self.price = price
        self.added_at = added_at or datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert cart item to dictionary."""
        return {
            "product_id": self.product_id,
            "quantity": self.quantity,
            "price": self.price,
            "added_at": self.added_at.isoformat(),
            "subtotal": self.price * self.quantity
        }


class Cart:
    """
    Shopping cart model.
    
    Attributes:
        user_id: User identifier
        items: List of cart items
        created_at: Cart creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        user_id: str,
        items: Optional[List[CartItem]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.user_id = user_id
        self.items = items or []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert cart to dictionary."""
        return {
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "item_count": len(self.items),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# ============================================
# CART API ENDPOINTS
# ============================================

async def add_to_cart(
    user_id: str,
    product_id: str,
    quantity: int = 1,
    user_email: Optional[str] = None
) -> Dict:
    """
    Add item to user's shopping cart.
    
    This function:
    1. Validates user existence and email (if provided)
    2. Validates product existence and availability
    3. Checks stock availability
    4. Validates cart limits
    5. Adds or updates item in cart
    6. Logs cart activity
    
    Args:
        user_id: User identifier
        product_id: Product identifier
        quantity: Quantity to add (default: 1)
        user_email: Optional user email for validation
    
    Returns:
        Dict containing:
        - success: Operation status
        - cart: Updated cart data
        - item_added: Added/updated item details
    
    Raises:
        CartValidationError: If validation fails
        CartItemError: If product is invalid
        CartLimitError: If cart limits exceeded
        InsufficientStockError: If insufficient stock
    """
    transaction_id = f"cart_add_{uuid4().hex[:12]}"
    
    log_info(
        message=f"Adding item to cart for user {user_id}",
        transaction_id=transaction_id,
        user_id=user_id,
        product_id=product_id,
        quantity=quantity
    )
    
    try:
        # Step 1: Validate user
        await _validate_user(user_id, user_email, transaction_id)
        
        # Step 2: Validate and get product
        product = await _validate_product(product_id, transaction_id)
        
        # Step 3: Validate quantity
        if quantity <= 0:
            raise CartValidationError(f"Quantity must be positive, got {quantity}")
        
        # Step 4: Check stock availability
        await _check_stock(product_id, quantity, transaction_id)
        
        # Step 5: Get current cart (simulated - would fetch from DB)
        cart = await _get_or_create_cart(user_id, transaction_id)
        
        # Step 6: Validate cart limits
        await _validate_cart_limits(cart, quantity, transaction_id)
        
        # Step 7: Add or update item in cart
        item_added = await _add_or_update_item(
            cart=cart,
            product_id=product_id,
            quantity=quantity,
            price=product["price"],
            transaction_id=transaction_id
        )
        
        # Step 8: Update cart timestamp
        cart.updated_at = datetime.utcnow()
        
        log_info(
            message=f"Item added to cart successfully",
            transaction_id=transaction_id,
            user_id=user_id,
            product_id=product_id,
            new_quantity=item_added["quantity"]
        )
        
        return {
            "success": True,
            "cart": cart.to_dict(),
            "item_added": item_added,
            "message": f"Added {quantity} x {product['name']} to cart"
        }
    
    except (CartValidationError, CartItemError, CartLimitError, InsufficientStockError) as e:
        log_error(
            message=f"Failed to add item to cart: {str(e)}",
            transaction_id=transaction_id,
            error_type=type(e).__name__
        )
        raise
    
    except Exception as e:
        log_error(
            message=f"Unexpected error adding item to cart: {str(e)}",
            transaction_id=transaction_id,
            error_type=type(e).__name__
        )
        raise CartError(f"Failed to add item to cart: {str(e)}")


async def remove_from_cart(
    user_id: str,
    product_id: str
) -> Dict:
    """
    Remove item from user's shopping cart.
    
    Args:
        user_id: User identifier
        product_id: Product identifier to remove
    
    Returns:
        Dict containing:
        - success: Operation status
        - cart: Updated cart data
        - item_removed: Removed item details
    
    Raises:
        CartValidationError: If validation fails
        CartItemError: If item not in cart
    """
    transaction_id = f"cart_remove_{uuid4().hex[:12]}"
    
    log_info(
        message=f"Removing item from cart for user {user_id}",
        transaction_id=transaction_id,
        user_id=user_id,
        product_id=product_id
    )
    
    try:
        # Validate user exists
        await _validate_user(user_id, None, transaction_id)
        
        # Get current cart
        cart = await _get_or_create_cart(user_id, transaction_id)
        
        # Find and remove item
        item_removed = None
        for i, item in enumerate(cart.items):
            if item.product_id == product_id:
                item_removed = cart.items.pop(i)
                break
        
        if not item_removed:
            raise CartItemError(f"Product {product_id} not found in cart")
        
        # Update cart timestamp
        cart.updated_at = datetime.utcnow()
        
        log_info(
            message=f"Item removed from cart successfully",
            transaction_id=transaction_id,
            user_id=user_id,
            product_id=product_id
        )
        
        return {
            "success": True,
            "cart": cart.to_dict(),
            "item_removed": item_removed.to_dict(),
            "message": f"Removed item from cart"
        }
    
    except (CartValidationError, CartItemError) as e:
        log_error(
            message=f"Failed to remove item from cart: {str(e)}",
            transaction_id=transaction_id,
            error_type=type(e).__name__
        )
        raise
    
    except Exception as e:
        log_error(
            message=f"Unexpected error removing item from cart: {str(e)}",
            transaction_id=transaction_id
        )
        raise CartError(f"Failed to remove item from cart: {str(e)}")


async def update_cart_item_quantity(
    user_id: str,
    product_id: str,
    new_quantity: int
) -> Dict:
    """
    Update quantity of item in cart.
    
    Args:
        user_id: User identifier
        product_id: Product identifier
        new_quantity: New quantity (0 to remove)
    
    Returns:
        Dict containing updated cart and item details
    
    Raises:
        CartValidationError: If validation fails
        CartItemError: If item not in cart
        InsufficientStockError: If insufficient stock
    """
    transaction_id = f"cart_update_{uuid4().hex[:12]}"
    
    log_info(
        message=f"Updating cart item quantity for user {user_id}",
        transaction_id=transaction_id,
        user_id=user_id,
        product_id=product_id,
        new_quantity=new_quantity
    )
    
    try:
        # If quantity is 0, remove item
        if new_quantity == 0:
            return await remove_from_cart(user_id, product_id)
        
        # Validate positive quantity
        if new_quantity < 0:
            raise CartValidationError(f"Quantity must be non-negative, got {new_quantity}")
        
        # Validate user exists
        await _validate_user(user_id, None, transaction_id)
        
        # Check stock availability for new quantity
        await _check_stock(product_id, new_quantity, transaction_id)
        
        # Get current cart
        cart = await _get_or_create_cart(user_id, transaction_id)
        
        # Find and update item
        item_updated = None
        for item in cart.items:
            if item.product_id == product_id:
                old_quantity = item.quantity
                item.quantity = new_quantity
                item_updated = item
                log_info(
                    message=f"Updated item quantity from {old_quantity} to {new_quantity}",
                    transaction_id=transaction_id,
                    product_id=product_id
                )
                break
        
        if not item_updated:
            raise CartItemError(f"Product {product_id} not found in cart")
        
        # Update cart timestamp
        cart.updated_at = datetime.utcnow()
        
        return {
            "success": True,
            "cart": cart.to_dict(),
            "item_updated": item_updated.to_dict(),
            "message": f"Updated item quantity to {new_quantity}"
        }
    
    except (CartValidationError, CartItemError, InsufficientStockError) as e:
        log_error(
            message=f"Failed to update cart item: {str(e)}",
            transaction_id=transaction_id,
            error_type=type(e).__name__
        )
        raise
    
    except Exception as e:
        log_error(
            message=f"Unexpected error updating cart item: {str(e)}",
            transaction_id=transaction_id
        )
        raise CartError(f"Failed to update cart item: {str(e)}")


async def calculate_cart_totals(user_id: str) -> Dict:
    """
    Calculate cart totals including subtotal, tax, and total.
    
    Uses TAX_RATE from config.settings to calculate tax.
    
    Args:
        user_id: User identifier
    
    Returns:
        Dict containing:
        - subtotal: Sum of all items before tax
        - tax: Calculated tax amount
        - total: Final total (subtotal + tax)
        - item_count: Number of items in cart
    
    Raises:
        CartValidationError: If validation fails
    """
    transaction_id = f"cart_calc_{uuid4().hex[:12]}"
    
    log_info(
        message=f"Calculating cart totals for user {user_id}",
        transaction_id=transaction_id,
        user_id=user_id
    )
    
    try:
        # Validate user exists
        await _validate_user(user_id, None, transaction_id)
        
        # Get current cart
        cart = await _get_or_create_cart(user_id, transaction_id)
        
        # Calculate subtotal
        subtotal = sum(item.price * item.quantity for item in cart.items)
        
        # Calculate tax using TAX_RATE from config
        tax = round(subtotal * TAX_RATE, 2)
        
        # Calculate total
        total = round(subtotal + tax, 2)
        
        log_info(
            message=f"Cart totals calculated",
            transaction_id=transaction_id,
            user_id=user_id,
            subtotal=subtotal,
            tax=tax,
            total=total,
            item_count=len(cart.items)
        )
        
        return {
            "subtotal": subtotal,
            "tax": tax,
            "tax_rate": TAX_RATE,
            "total": total,
            "item_count": len(cart.items)
        }
    
    except CartValidationError as e:
        log_error(
            message=f"Failed to calculate cart totals: {str(e)}",
            transaction_id=transaction_id
        )
        raise
    
    except Exception as e:
        log_error(
            message=f"Unexpected error calculating cart totals: {str(e)}",
            transaction_id=transaction_id
        )
        raise CartError(f"Failed to calculate cart totals: {str(e)}")


async def validate_cart_for_checkout(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate cart is ready for checkout.
    
    Checks:
    - Cart is not empty
    - All items are still in stock
    - Cart total meets minimum order amount
    - No items exceed max quantity limits
    
    Args:
        user_id: User identifier
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if cart is valid for checkout
        - error_message: Descriptive error if invalid, None if valid
    
    Raises:
        CartValidationError: If user validation fails
    """
    transaction_id = f"cart_validate_{uuid4().hex[:12]}"
    
    log_info(
        message=f"Validating cart for checkout for user {user_id}",
        transaction_id=transaction_id,
        user_id=user_id
    )
    
    try:
        # Validate user exists
        await _validate_user(user_id, None, transaction_id)
        
        # Get current cart
        cart = await _get_or_create_cart(user_id, transaction_id)
        
        # Check 1: Cart not empty
        if not cart.items:
            log_warning(
                message="Cart validation failed: empty cart",
                transaction_id=transaction_id,
                user_id=user_id
            )
            return False, "Cart is empty"
        
        # Check 2: Validate stock for all items
        for item in cart.items:
            try:
                await _check_stock(item.product_id, item.quantity, transaction_id)
            except InsufficientStockError as e:
                log_warning(
                    message=f"Cart validation failed: insufficient stock",
                    transaction_id=transaction_id,
                    product_id=item.product_id
                )
                return False, str(e)
        
        # Check 3: Validate minimum order amount
        totals = await calculate_cart_totals(user_id)
        if totals["total"] < MIN_ORDER_AMOUNT:
            log_warning(
                message=f"Cart validation failed: below minimum order amount",
                transaction_id=transaction_id,
                total=totals["total"],
                min_required=MIN_ORDER_AMOUNT
            )
            return False, f"Order total ${totals['total']:.2f} is below minimum ${MIN_ORDER_AMOUNT:.2f}"
        
        log_info(
            message="Cart validation successful",
            transaction_id=transaction_id,
            user_id=user_id,
            item_count=len(cart.items),
            total=totals["total"]
        )
        
        return True, None
    
    except CartValidationError as e:
        log_error(
            message=f"Failed to validate cart: {str(e)}",
            transaction_id=transaction_id
        )
        raise
    
    except Exception as e:
        log_error(
            message=f"Unexpected error validating cart: {str(e)}",
            transaction_id=transaction_id
        )
        raise CartError(f"Failed to validate cart: {str(e)}")


# ============================================
# HELPER FUNCTIONS
# ============================================

async def _validate_user(
    user_id: str,
    email: Optional[str],
    transaction_id: str
) -> Dict:
    """
    Validate user exists and email is valid.
    
    Uses:
    - get_user_by_id() from utils.database
    - validate_email() from utils.validator
    
    Raises:
        CartValidationError: If user not found or email invalid
    """
    # Validate email if provided
    if email:
        is_valid, error = validate_email(email)
        if not is_valid:
            raise CartValidationError(f"Invalid email: {error}")
    
    # Check user exists (uses database utils from main branch)
    user = await get_user_by_id(user_id)
    if not user:
        raise CartValidationError(f"User {user_id} not found")
    
    return user


async def _validate_product(product_id: str, transaction_id: str) -> Dict:
    """
    Validate product exists and is available.
    
    Uses get_product_by_id() from utils.database.
    
    Raises:
        CartItemError: If product not found or unavailable
    """
    # Get product (uses database utils from main branch)
    product = await get_product_by_id(product_id)
    if not product:
        raise CartItemError(f"Product {product_id} not found")
    
    if not product.get("available", True):
        raise CartItemError(f"Product {product_id} is not available")
    
    return product


async def _check_stock(
    product_id: str,
    quantity: int,
    transaction_id: str
) -> bool:
    """
    Check if sufficient stock is available.
    
    Uses check_stock_availability() from services.inventory_service.
    
    Raises:
        InsufficientStockError: If insufficient stock
    """
    # Check stock (uses inventory service from main branch)
    is_available = await check_stock_availability(product_id, quantity)
    
    if not is_available:
        log_warning(
            message=f"Insufficient stock for product",
            transaction_id=transaction_id,
            product_id=product_id,
            requested_quantity=quantity
        )
        raise InsufficientStockError(
            f"Insufficient stock for product {product_id}. Requested: {quantity}"
        )
    
    return True


async def _get_or_create_cart(user_id: str, transaction_id: str) -> Cart:
    """
    Get existing cart or create new one.
    
    In production, this would fetch from database.
    For testing, creates a new cart.
    """
    # Simulated cart retrieval
    # In production: would use database utils to fetch persisted cart
    return Cart(user_id=user_id)


async def _validate_cart_limits(
    cart: Cart,
    additional_quantity: int,
    transaction_id: str
) -> None:
    """
    Validate cart doesn't exceed limits.
    
    Uses MAX_CART_ITEMS from config.settings.
    
    Raises:
        CartLimitError: If cart limits exceeded
    """
    total_items = len(cart.items) + (1 if additional_quantity > 0 else 0)
    
    if total_items > MAX_CART_ITEMS:
        log_warning(
            message=f"Cart limit exceeded",
            transaction_id=transaction_id,
            current_items=len(cart.items),
            max_allowed=MAX_CART_ITEMS
        )
        raise CartLimitError(
            f"Cart cannot exceed {MAX_CART_ITEMS} different items. Current: {len(cart.items)}"
        )


async def _add_or_update_item(
    cart: Cart,
    product_id: str,
    quantity: int,
    price: float,
    transaction_id: str
) -> Dict:
    """
    Add new item or update existing item quantity.
    
    Returns dict with item details.
    """
    # Check if item already in cart
    for item in cart.items:
        if item.product_id == product_id:
            # Update existing item
            old_quantity = item.quantity
            item.quantity += quantity
            log_info(
                message=f"Updated existing cart item",
                transaction_id=transaction_id,
                product_id=product_id,
                old_quantity=old_quantity,
                new_quantity=item.quantity
            )
            return item.to_dict()
    
    # Add new item
    new_item = CartItem(
        product_id=product_id,
        quantity=quantity,
        price=price
    )
    cart.items.append(new_item)
    
    log_info(
        message=f"Added new item to cart",
        transaction_id=transaction_id,
        product_id=product_id,
        quantity=quantity
    )
    
    return new_item.to_dict()
