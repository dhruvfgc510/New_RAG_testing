"""
Order model with tax calculation and item management.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from config.settings import TAX_RATE


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderItem:
    """
    Represents a single item in an order.
    
    Attributes:
        product_id: Product identifier
        product_name: Product name (snapshot)
        quantity: Quantity ordered
        unit_price: Price per unit at time of order
        total_price: Total price for this item
    """
    
    def __init__(
        self,
        product_id: str,
        product_name: str,
        quantity: int,
        unit_price: float
    ):
        """
        Initialize OrderItem.
        
        Args:
            product_id: Product identifier
            product_name: Product name
            quantity: Quantity ordered
            unit_price: Price per unit
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = quantity * unit_price
    
    def to_dict(self) -> Dict[str, any]:
        """Convert OrderItem to dictionary."""
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'OrderItem':
        """Create OrderItem from dictionary."""
        return cls(
            product_id=data['product_id'],
            product_name=data['product_name'],
            quantity=data['quantity'],
            unit_price=data['unit_price'],
        )
    
    def __repr__(self) -> str:
        """String representation of OrderItem."""
        return f"OrderItem(product='{self.product_name}', quantity={self.quantity}, total=${self.total_price:.2f})"


class Order:
    """
    Order model representing a customer purchase.
    
    Attributes:
        order_id: Unique order identifier
        user_id: User identifier
        items: List of order items
        subtotal: Subtotal before tax
        tax_amount: Tax amount
        total_amount: Total amount including tax
        status: Order status
        shipping_address: Shipping address
        payment_transaction_id: Payment transaction ID
        created_at: Order creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        order_id: str,
        user_id: str,
        items: List[OrderItem],
        shipping_address: Dict[str, str],
        payment_transaction_id: Optional[str] = None,
        status: OrderStatus = OrderStatus.PENDING,
        created_at: Optional[datetime] = None
    ):
        """
        Initialize Order instance.
        
        Args:
            order_id: Unique order identifier
            user_id: User identifier
            items: List of order items
            shipping_address: Shipping address
            payment_transaction_id: Payment transaction ID
            status: Order status
            created_at: Order creation timestamp
        """
        if not items:
            raise ValueError("Order must contain at least one item")
        
        self.order_id = order_id
        self.user_id = user_id
        self.items = items
        self.shipping_address = shipping_address
        self.payment_transaction_id = payment_transaction_id
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = self.created_at
        
        # Calculate amounts
        self.subtotal = self._calculate_subtotal()
        self.tax_amount = self.calculate_tax()
        self.total_amount = self.subtotal + self.tax_amount
    
    def _calculate_subtotal(self) -> float:
        """
        Calculate order subtotal (sum of all items).
        
        Returns:
            Subtotal amount
        """
        return sum(item.total_price for item in self.items)
    
    def calculate_tax(self) -> float:
        """
        Calculate tax amount based on TAX_RATE from settings.
        
        Returns:
            Tax amount
            
        Examples:
            >>> order = Order(...)
            >>> tax = order.calculate_tax()
            >>> print(f"Tax: ${tax:.2f}")
        """
        return self.subtotal * TAX_RATE
    
    def add_item(self, item: OrderItem):
        """
        Add item to order.
        
        Args:
            item: OrderItem to add
            
        Note:
            This recalculates subtotal, tax, and total
        """
        self.items.append(item)
        self.subtotal = self._calculate_subtotal()
        self.tax_amount = self.calculate_tax()
        self.total_amount = self.subtotal + self.tax_amount
        self.updated_at = datetime.utcnow()
    
    def remove_item(self, product_id: str) -> bool:
        """
        Remove item from order by product ID.
        
        Args:
            product_id: Product identifier
            
        Returns:
            True if item was removed, False if not found
        """
        original_length = len(self.items)
        self.items = [item for item in self.items if item.product_id != product_id]
        
        if len(self.items) < original_length:
            self.subtotal = self._calculate_subtotal()
            self.tax_amount = self.calculate_tax()
            self.total_amount = self.subtotal + self.tax_amount
            self.updated_at = datetime.utcnow()
            return True
        
        return False
    
    def update_status(self, new_status: OrderStatus):
        """
        Update order status.
        
        Args:
            new_status: New order status
        """
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    def get_item_count(self) -> int:
        """
        Get total number of items in order.
        
        Returns:
            Total item count (sum of all quantities)
        """
        return sum(item.quantity for item in self.items)
    
    def get_item_by_product_id(self, product_id: str) -> Optional[OrderItem]:
        """
        Get order item by product ID.
        
        Args:
            product_id: Product identifier
            
        Returns:
            OrderItem if found, None otherwise
        """
        for item in self.items:
            if item.product_id == product_id:
                return item
        return None
    
    def is_editable(self) -> bool:
        """
        Check if order can be edited.
        
        Returns:
            True if order is in pending or processing status
        """
        return self.status in [OrderStatus.PENDING, OrderStatus.PROCESSING]
    
    def can_be_cancelled(self) -> bool:
        """
        Check if order can be cancelled.
        
        Returns:
            True if order hasn't been shipped yet
        """
        return self.status in [OrderStatus.PENDING, OrderStatus.PROCESSING]
    
    def cancel(self):
        """
        Cancel the order.
        
        Raises:
            ValueError: If order cannot be cancelled
        """
        if not self.can_be_cancelled():
            raise ValueError(f"Cannot cancel order with status: {self.status.value}")
        
        self.update_status(OrderStatus.CANCELLED)
    
    def to_dict(self) -> Dict[str, any]:
        """
        Convert order to dictionary representation.
        
        Returns:
            Order data as dictionary
        """
        return {
            'order_id': self.order_id,
            'user_id': self.user_id,
            'items': [item.to_dict() for item in self.items],
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'status': self.status.value,
            'shipping_address': self.shipping_address,
            'payment_transaction_id': self.payment_transaction_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'Order':
        """
        Create Order instance from dictionary.
        
        Args:
            data: Order data dictionary
            
        Returns:
            Order instance
        """
        items = [OrderItem.from_dict(item_data) for item_data in data['items']]
        
        return cls(
            order_id=data['order_id'],
            user_id=data['user_id'],
            items=items,
            shipping_address=data['shipping_address'],
            payment_transaction_id=data.get('payment_transaction_id'),
            status=OrderStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
        )
    
    def __repr__(self) -> str:
        """String representation of Order."""
        return f"Order(order_id='{self.order_id}', total=${self.total_amount:.2f}, status='{self.status.value}')"
    
    def __eq__(self, other) -> bool:
        """Check equality based on order_id."""
        if not isinstance(other, Order):
            return False
        return self.order_id == other.order_id
