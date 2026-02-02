"""
Product model with inventory tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class ProductCategory(Enum):
    """Product category enumeration."""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"
    HOME = "home"
    SPORTS = "sports"
    TOYS = "toys"
    FOOD = "food"
    OTHER = "other"


class Product:
    """
    Product model representing an item for sale.
    
    Attributes:
        product_id: Unique product identifier
        name: Product name
        description: Product description
        price: Product price in USD
        category: Product category
        stock_quantity: Available stock
        image_url: Product image URL
        seller_id: Seller user ID
        created_at: Product creation timestamp
        is_active: Product active status
    """
    
    def __init__(
        self,
        product_id: str,
        name: str,
        description: str,
        price: float,
        category: ProductCategory,
        stock_quantity: int = 0,
        image_url: Optional[str] = None,
        seller_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        is_active: bool = True
    ):
        """
        Initialize Product instance.
        
        Args:
            product_id: Unique product identifier
            name: Product name
            description: Product description
            price: Product price
            category: Product category
            stock_quantity: Available stock
            image_url: Product image URL
            seller_id: Seller user ID
            created_at: Product creation timestamp
            is_active: Product active status
        """
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.stock_quantity = stock_quantity
        self.image_url = image_url
        self.seller_id = seller_id
        self.created_at = created_at or datetime.utcnow()
        self.is_active = is_active
    
    def to_dict(self) -> Dict[str, any]:
        """
        Convert product to dictionary representation.
        
        Returns:
            Product data as dictionary
        """
        return {
            'product_id': self.product_id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category.value,
            'stock_quantity': self.stock_quantity,
            'image_url': self.image_url,
            'seller_id': self.seller_id,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'Product':
        """
        Create Product instance from dictionary.
        
        Args:
            data: Product data dictionary
            
        Returns:
            Product instance
        """
        return cls(
            product_id=data['product_id'],
            name=data['name'],
            description=data['description'],
            price=data['price'],
            category=ProductCategory(data['category']),
            stock_quantity=data.get('stock_quantity', 0),
            image_url=data.get('image_url'),
            seller_id=data.get('seller_id'),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
            is_active=data.get('is_active', True),
        )
    
    def update_price(self, new_price: float):
        """
        Update product price.
        
        Args:
            new_price: New price
            
        Raises:
            ValueError: If price is negative
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        self.price = new_price
    
    def update_stock(self, quantity_change: int):
        """
        Update stock quantity.
        
        Args:
            quantity_change: Change in quantity (positive or negative)
            
        Raises:
            ValueError: If resulting stock would be negative
        """
        new_quantity = self.stock_quantity + quantity_change
        if new_quantity < 0:
            raise ValueError(f"Insufficient stock: current={self.stock_quantity}, change={quantity_change}")
        self.stock_quantity = new_quantity
    
    def is_in_stock(self) -> bool:
        """
        Check if product is in stock.
        
        Returns:
            True if stock quantity > 0
        """
        return self.stock_quantity > 0
    
    def is_low_stock(self, threshold: int = 10) -> bool:
        """
        Check if product has low stock.
        
        Args:
            threshold: Low stock threshold
            
        Returns:
            True if stock is below threshold
        """
        return 0 < self.stock_quantity < threshold
    
    def deactivate(self):
        """Deactivate product (hide from store)."""
        self.is_active = False
    
    def activate(self):
        """Activate product (show in store)."""
        self.is_active = True
    
    def get_discounted_price(self, discount_percentage: float) -> float:
        """
        Calculate discounted price.
        
        Args:
            discount_percentage: Discount percentage (0-100)
            
        Returns:
            Discounted price
            
        Raises:
            ValueError: If discount percentage is invalid
        """
        if discount_percentage < 0 or discount_percentage > 100:
            raise ValueError("Discount percentage must be between 0 and 100")
        
        discount_amount = self.price * (discount_percentage / 100)
        return self.price - discount_amount
    
    def __repr__(self) -> str:
        """String representation of Product."""
        return f"Product(product_id='{self.product_id}', name='{self.name}', price=${self.price:.2f})"
    
    def __eq__(self, other) -> bool:
        """Check equality based on product_id."""
        if not isinstance(other, Product):
            return False
        return self.product_id == other.product_id
