"""
Input validation utilities for e-commerce application.

Provides comprehensive validation for:
- Email addresses (RFC 5322 compliant)
- Credit card numbers (Luhn algorithm)
- Physical addresses
- Phone numbers
- ZIP codes
"""

import re
from typing import Dict, List, Optional, Tuple


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address according to RFC 5322 standard.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_email("user@example.com")
        (True, None)
        >>> validate_email("invalid-email")
        (False, "Invalid email format")
    """
    if not email or not isinstance(email, str):
        return False, "Email cannot be empty"
    
    # RFC 5322 compliant regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    # Check for common typos
    common_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
    domain = email.split('@')[1].lower()
    
    # Check for suspicious patterns
    if '..' in email:
        return False, "Email contains consecutive dots"
    
    if email.startswith('.') or email.endswith('.'):
        return False, "Email cannot start or end with a dot"
    
    # Check email length
    if len(email) > 254:
        return False, "Email address too long (max 254 characters)"
    
    local_part = email.split('@')[0]
    if len(local_part) > 64:
        return False, "Local part of email too long (max 64 characters)"
    
    return True, None


def validate_credit_card(card_number: str) -> Tuple[bool, Optional[str]]:
    """
    Validate credit card number using Luhn algorithm.
    
    The Luhn algorithm is used by most credit card companies to validate
    card numbers and detect accidental errors.
    
    Args:
        card_number: Credit card number (can include spaces/dashes)
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_credit_card("4532015112830366")
        (True, None)
        >>> validate_credit_card("1234567890123456")
        (False, "Invalid card number (failed Luhn check)")
    """
    if not card_number or not isinstance(card_number, str):
        return False, "Card number cannot be empty"
    
    # Remove spaces and dashes
    card_number = card_number.replace(' ', '').replace('-', '')
    
    # Check if only digits
    if not card_number.isdigit():
        return False, "Card number must contain only digits"
    
    # Check length (most cards are 13-19 digits)
    if len(card_number) < 13 or len(card_number) > 19:
        return False, f"Invalid card length: {len(card_number)} digits (expected 13-19)"
    
    # Luhn algorithm implementation
    def luhn_checksum(card_num: str) -> bool:
        """Calculate Luhn checksum."""
        digits = [int(d) for d in card_num]
        checksum = 0
        
        # Process every second digit from right to left
        for i in range(len(digits) - 2, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
        
        checksum = sum(digits)
        return checksum % 10 == 0
    
    if not luhn_checksum(card_number):
        return False, "Invalid card number (failed Luhn check)"
    
    # Validate card type by BIN (Bank Identification Number)
    card_type = _identify_card_type(card_number)
    if not card_type:
        return False, "Unknown card type"
    
    return True, None


def _identify_card_type(card_number: str) -> Optional[str]:
    """
    Identify credit card type based on BIN (Bank Identification Number).
    
    Args:
        card_number: Credit card number
        
    Returns:
        Card type or None if unknown
    """
    patterns = {
        'visa': r'^4[0-9]{12}(?:[0-9]{3})?$',
        'mastercard': r'^5[1-5][0-9]{14}$',
        'amex': r'^3[47][0-9]{13}$',
        'discover': r'^6(?:011|5[0-9]{2})[0-9]{12}$',
    }
    
    for card_type, pattern in patterns.items():
        if re.match(pattern, card_number):
            return card_type
    
    return None


def validate_address(address: Dict[str, str]) -> Tuple[bool, Optional[str]]:
    """
    Validate physical address for shipping.
    
    Args:
        address: Dictionary containing address fields:
            - street: Street address
            - city: City name
            - state: State/province code
            - zip_code: ZIP/postal code
            - country: Country code (ISO 3166-1 alpha-2)
            
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> address = {
        ...     "street": "123 Main St",
        ...     "city": "Springfield",
        ...     "state": "IL",
        ...     "zip_code": "62701",
        ...     "country": "US"
        ... }
        >>> validate_address(address)
        (True, None)
    """
    if not address or not isinstance(address, dict):
        return False, "Address must be a dictionary"
    
    # Required fields
    required_fields = ['street', 'city', 'state', 'zip_code', 'country']
    missing_fields = [field for field in required_fields if field not in address]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Validate street address
    street = address.get('street', '').strip()
    if not street or len(street) < 5:
        return False, "Street address too short (min 5 characters)"
    
    if len(street) > 100:
        return False, "Street address too long (max 100 characters)"
    
    # Validate city
    city = address.get('city', '').strip()
    if not city or len(city) < 2:
        return False, "City name too short (min 2 characters)"
    
    if len(city) > 50:
        return False, "City name too long (max 50 characters)"
    
    # Validate state (US format: 2 letters)
    state = address.get('state', '').strip().upper()
    if address.get('country') == 'US':
        if not re.match(r'^[A-Z]{2}$', state):
            return False, "Invalid state code (expected 2-letter code)"
        
        # Validate against known US states
        valid_states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        ]
        
        if state not in valid_states:
            return False, f"Invalid US state code: {state}"
    
    # Validate ZIP code
    zip_code = address.get('zip_code', '').strip()
    if address.get('country') == 'US':
        # US ZIP: 5 digits or 5+4 format
        if not re.match(r'^\d{5}(-\d{4})?$', zip_code):
            return False, "Invalid US ZIP code (expected 12345 or 12345-6789)"
    else:
        # Generic validation for other countries
        if not zip_code or len(zip_code) < 3:
            return False, "ZIP/postal code too short"
    
    # Validate country code (ISO 3166-1 alpha-2)
    country = address.get('country', '').strip().upper()
    if not re.match(r'^[A-Z]{2}$', country):
        return False, "Invalid country code (expected 2-letter ISO code)"
    
    return True, None


def validate_phone_number(phone: str, country_code: str = 'US') -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        country_code: Country code for format validation
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone or not isinstance(phone, str):
        return False, "Phone number cannot be empty"
    
    # Remove common formatting characters
    phone = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    if country_code == 'US':
        # US format: 10 digits
        if not re.match(r'^\d{10}$', phone):
            return False, "Invalid US phone number (expected 10 digits)"
        
        # Check for invalid area codes
        area_code = phone[:3]
        if area_code[0] in ['0', '1']:
            return False, f"Invalid area code: {area_code}"
    
    return True, None
