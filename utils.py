"""
Self-Contained Utility Functions.

SCENARIO 3: No Missing Dependencies
This file is part of the PR and provides all utility functions needed.
NO imports from main branch - everything is self-contained.
"""

import re
from datetime import datetime
from typing import Dict, Optional


# ============================================
# VALIDATION UTILITIES
# ============================================

def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Simple email validation (not RFC 5322 compliant).
    This is a self-contained version - no external dependencies.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Simple regex pattern for email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_address(address: Dict) -> bool:
    """
    Validate shipping address has required fields.
    
    Self-contained validation - no external dependencies.
    
    Args:
        address: Address dictionary
    
    Returns:
        True if valid, False otherwise
    """
    if not address or not isinstance(address, dict):
        return False
    
    required_fields = ["street", "city", "state", "zip_code", "country"]
    
    for field in required_fields:
        if field not in address or not address[field]:
            return False
    
    # Validate zip code format (US only, simplified)
    zip_code = str(address.get("zip_code", ""))
    if not re.match(r'^\d{5}(-\d{4})?$', zip_code):
        return False
    
    return True


def validate_credit_card(card_number: str) -> bool:
    """
    Validate credit card number using Luhn algorithm.
    
    Self-contained validation - no external dependencies.
    
    Args:
        card_number: Credit card number
    
    Returns:
        True if valid, False otherwise
    """
    if not card_number or not isinstance(card_number, str):
        return False
    
    # Remove spaces and dashes
    card_number = re.sub(r'[\s-]', '', card_number)
    
    # Check if all digits
    if not card_number.isdigit():
        return False
    
    # Check length (13-19 digits)
    if not 13 <= len(card_number) <= 19:
        return False
    
    # Luhn algorithm
    def luhn_check(card: str) -> bool:
        digits = [int(d) for d in card]
        checksum = 0
        
        for i in range(len(digits) - 2, -1, -1):
            if (len(digits) - 1 - i) % 2 == 1:
                digits[i] *= 2
                if digits[i] > 9:
                    digits[i] -= 9
        
        return sum(digits) % 10 == 0
    
    return luhn_check(card_number)


# ============================================
# LOGGING UTILITIES
# ============================================

def log_info(message: str, transaction_id: Optional[str] = None):
    """
    Log informational message.
    
    Self-contained logging - prints to console.
    No external logging infrastructure needed.
    
    Args:
        message: Message to log
        transaction_id: Optional transaction identifier
    """
    timestamp = datetime.utcnow().isoformat()
    if transaction_id:
        print(f"[INFO] {timestamp} [{transaction_id}] {message}")
    else:
        print(f"[INFO] {timestamp} {message}")


def log_error(message: str, transaction_id: Optional[str] = None):
    """
    Log error message.
    
    Self-contained logging - prints to console.
    
    Args:
        message: Error message to log
        transaction_id: Optional transaction identifier
    """
    timestamp = datetime.utcnow().isoformat()
    if transaction_id:
        print(f"[ERROR] {timestamp} [{transaction_id}] {message}")
    else:
        print(f"[ERROR] {timestamp} {message}")


def log_warning(message: str, transaction_id: Optional[str] = None):
    """
    Log warning message.
    
    Self-contained logging - prints to console.
    
    Args:
        message: Warning message to log
        transaction_id: Optional transaction identifier
    """
    timestamp = datetime.utcnow().isoformat()
    if transaction_id:
        print(f"[WARNING] {timestamp} [{transaction_id}] {message}")
    else:
        print(f"[WARNING] {timestamp} {message}")
