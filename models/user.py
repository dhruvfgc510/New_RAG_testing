"""
User model with authentication and profile management.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class UserRole(Enum):
    """User role enumeration."""
    CUSTOMER = "customer"
    ADMIN = "admin"
    SELLER = "seller"


class User:
    """
    User model representing a customer or admin.
    
    Attributes:
        user_id: Unique user identifier
        email: User email address
        name: User full name
        role: User role (customer, admin, seller)
        created_at: Account creation timestamp
        is_active: Account active status
        address: Shipping address
        phone: Phone number
    """
    
    def __init__(
        self,
        user_id: str,
        email: str,
        name: str,
        role: UserRole = UserRole.CUSTOMER,
        created_at: Optional[datetime] = None,
        is_active: bool = True,
        address: Optional[Dict[str, str]] = None,
        phone: Optional[str] = None
    ):
        """
        Initialize User instance.
        
        Args:
            user_id: Unique user identifier
            email: User email address
            name: User full name
            role: User role
            created_at: Account creation timestamp
            is_active: Account active status
            address: Shipping address dictionary
            phone: Phone number
        """
        self.user_id = user_id
        self.email = email
        self.name = name
        self.role = role
        self.created_at = created_at or datetime.utcnow()
        self.is_active = is_active
        self.address = address or {}
        self.phone = phone
    
    def to_dict(self) -> Dict[str, any]:
        """
        Convert user to dictionary representation.
        
        Returns:
            User data as dictionary
        """
        return {
            'user_id': self.user_id,
            'email': self.email,
            'name': self.name,
            'role': self.role.value,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'address': self.address,
            'phone': self.phone,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'User':
        """
        Create User instance from dictionary.
        
        Args:
            data: User data dictionary
            
        Returns:
            User instance
        """
        return cls(
            user_id=data['user_id'],
            email=data['email'],
            name=data['name'],
            role=UserRole(data.get('role', 'customer')),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
            is_active=data.get('is_active', True),
            address=data.get('address'),
            phone=data.get('phone'),
        )
    
    def update_address(self, address: Dict[str, str]):
        """
        Update user's shipping address.
        
        Args:
            address: New shipping address
        """
        self.address = address
    
    def update_phone(self, phone: str):
        """
        Update user's phone number.
        
        Args:
            phone: New phone number
        """
        self.phone = phone
    
    def deactivate(self):
        """Deactivate user account."""
        self.is_active = False
    
    def activate(self):
        """Activate user account."""
        self.is_active = True
    
    def is_admin(self) -> bool:
        """
        Check if user has admin role.
        
        Returns:
            True if user is admin
        """
        return self.role == UserRole.ADMIN
    
    def is_seller(self) -> bool:
        """
        Check if user has seller role.
        
        Returns:
            True if user is seller
        """
        return self.role == UserRole.SELLER
    
    def __repr__(self) -> str:
        """String representation of User."""
        return f"User(user_id='{self.user_id}', email='{self.email}', role='{self.role.value}')"
    
    def __eq__(self, other) -> bool:
        """Check equality based on user_id."""
        if not isinstance(other, User):
            return False
        return self.user_id == other.user_id
