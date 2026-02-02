"""
Payment processing service with gateway integration.

Provides secure payment processing with:
- Multiple payment gateway support
- Retry logic with exponential backoff
- Comprehensive error handling
- Transaction logging
- PCI-DSS compliance considerations
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Tuple
from uuid import uuid4

from utils.logger import (
    log_payment_attempt,
    log_payment_success,
    log_payment_failure,
    log_error,
)
from config.settings import (
    PAYMENT_GATEWAY_URL,
    PAYMENT_TIMEOUT_SECONDS,
    MAX_PAYMENT_RETRIES,
)


class PaymentStatus(Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentError(Exception):
    """Base exception for payment errors."""
    pass


class PaymentGatewayError(PaymentError):
    """Exception for payment gateway errors."""
    pass


class InsufficientFundsError(PaymentError):
    """Exception for insufficient funds."""
    pass


class InvalidCardError(PaymentError):
    """Exception for invalid card details."""
    pass


async def process_payment(
    amount: float,
    card_data: Dict[str, str],
    order_id: str,
    user_id: str,
    retry_count: int = 0
) -> Dict[str, any]:
    """
    Process payment through payment gateway with retry logic.
    
    Implements:
    - Retry logic with exponential backoff
    - Comprehensive error handling
    - Transaction logging
    - Timeout handling
    
    Args:
        amount: Payment amount in USD
        card_data: Dictionary containing:
            - card_number: Credit card number
            - expiry_month: Expiry month (MM)
            - expiry_year: Expiry year (YYYY)
            - cvv: Card CVV
            - cardholder_name: Cardholder name
        order_id: Order identifier
        user_id: User identifier
        retry_count: Current retry attempt (internal)
        
    Returns:
        Dictionary containing:
            - status: Payment status
            - transaction_id: Gateway transaction ID
            - amount: Processed amount
            - timestamp: Processing timestamp
            
    Raises:
        PaymentGatewayError: If gateway communication fails
        InsufficientFundsError: If card has insufficient funds
        InvalidCardError: If card details are invalid
        
    Examples:
        >>> card_data = {
        ...     "card_number": "4532015112830366",
        ...     "expiry_month": "12",
        ...     "expiry_year": "2025",
        ...     "cvv": "123",
        ...     "cardholder_name": "John Doe"
        ... }
        >>> result = await process_payment(99.99, card_data, "order_123", "user_123")
        >>> print(result['status'])
        'completed'
    """
    # Validate amount
    if amount <= 0:
        raise ValueError("Payment amount must be positive")
    
    if amount > 10000:
        raise ValueError("Payment amount exceeds maximum limit ($10,000)")
    
    # Validate required card data fields
    required_fields = ['card_number', 'expiry_month', 'expiry_year', 'cvv']
    missing_fields = [field for field in required_fields if field not in card_data]
    
    if missing_fields:
        raise InvalidCardError(f"Missing card data fields: {', '.join(missing_fields)}")
    
    # Generate transaction ID
    transaction_id = f"txn_{uuid4().hex[:16]}"
    
    # Log payment attempt
    log_payment_attempt(
        transaction_id=transaction_id,
        amount=amount,
        gateway="stripe",
        attempt_number=retry_count + 1
    )
    
    try:
        # Process payment through gateway
        gateway_response = await _call_payment_gateway(
            amount=amount,
            card_data=card_data,
            transaction_id=transaction_id
        )
        
        # Parse gateway response
        if gateway_response['status'] == 'success':
            # Log successful payment
            log_payment_success(
                transaction_id=transaction_id,
                amount=amount,
                gateway="stripe",
                gateway_transaction_id=gateway_response['gateway_transaction_id']
            )
            
            return {
                'status': PaymentStatus.COMPLETED.value,
                'transaction_id': transaction_id,
                'gateway_transaction_id': gateway_response['gateway_transaction_id'],
                'amount': amount,
                'timestamp': datetime.utcnow().isoformat(),
                'order_id': order_id,
                'user_id': user_id,
            }
        
        elif gateway_response['status'] == 'insufficient_funds':
            raise InsufficientFundsError("Card has insufficient funds")
        
        elif gateway_response['status'] == 'invalid_card':
            raise InvalidCardError(f"Invalid card: {gateway_response.get('message', 'Unknown error')}")
        
        else:
            # Gateway returned error - determine if retryable
            if _is_retryable_error(gateway_response) and retry_count < MAX_PAYMENT_RETRIES:
                # Log retry attempt
                log_error(
                    error_message=f"Payment gateway error (attempt {retry_count + 1}/{MAX_PAYMENT_RETRIES})",
                    error_type="PaymentGatewayError",
                    transaction_id=transaction_id,
                    extra={
                        'gateway_response': gateway_response,
                        'will_retry': True,
                    }
                )
                
                # Wait with exponential backoff
                backoff_seconds = 2 ** retry_count
                await asyncio.sleep(backoff_seconds)
                
                # Retry payment
                return await process_payment(
                    amount=amount,
                    card_data=card_data,
                    order_id=order_id,
                    user_id=user_id,
                    retry_count=retry_count + 1
                )
            else:
                # Non-retryable error or max retries exceeded
                error_message = gateway_response.get('message', 'Unknown error')
                
                log_payment_failure(
                    transaction_id=transaction_id,
                    amount=amount,
                    gateway="stripe",
                    error_code=gateway_response.get('error_code', 'UNKNOWN'),
                    error_message=error_message
                )
                
                raise PaymentGatewayError(f"Payment failed: {error_message}")
    
    except asyncio.TimeoutError:
        log_error(
            error_message=f"Payment gateway timeout (attempt {retry_count + 1})",
            error_type="PaymentTimeout",
            transaction_id=transaction_id
        )
        
        if retry_count < MAX_PAYMENT_RETRIES:
            # Retry on timeout
            backoff_seconds = 2 ** retry_count
            await asyncio.sleep(backoff_seconds)
            
            return await process_payment(
                amount=amount,
                card_data=card_data,
                order_id=order_id,
                user_id=user_id,
                retry_count=retry_count + 1
            )
        else:
            raise PaymentGatewayError("Payment gateway timeout after maximum retries")


async def _call_payment_gateway(
    amount: float,
    card_data: Dict[str, str],
    transaction_id: str
) -> Dict[str, any]:
    """
    Call payment gateway API.
    
    Args:
        amount: Payment amount
        card_data: Card information
        transaction_id: Transaction identifier
        
    Returns:
        Gateway response dictionary
    """
    # Simulate payment gateway API call
    try:
        # In production, this would make actual HTTP request to gateway
        # using aiohttp or similar library:
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(
        #         PAYMENT_GATEWAY_URL,
        #         json={...},
        #         timeout=PAYMENT_TIMEOUT_SECONDS
        #     ) as response:
        #         return await response.json()
        
        # Simulate network delay
        await asyncio.wait_for(
            asyncio.sleep(0.5),
            timeout=PAYMENT_TIMEOUT_SECONDS
        )
        
        # Simulate successful response
        return {
            'status': 'success',
            'gateway_transaction_id': f"gw_{uuid4().hex[:12]}",
            'timestamp': datetime.utcnow().isoformat(),
        }
    
    except asyncio.TimeoutError:
        raise


def _is_retryable_error(gateway_response: Dict[str, any]) -> bool:
    """
    Determine if gateway error is retryable.
    
    Args:
        gateway_response: Response from payment gateway
        
    Returns:
        True if error is retryable
    """
    retryable_codes = [
        'gateway_timeout',
        'service_unavailable',
        'rate_limit_exceeded',
        'network_error',
    ]
    
    error_code = gateway_response.get('error_code', '').lower()
    return error_code in retryable_codes


async def refund_payment(
    transaction_id: str,
    amount: Optional[float] = None,
    reason: str = "customer_request"
) -> Dict[str, any]:
    """
    Process payment refund.
    
    Args:
        transaction_id: Original transaction ID to refund
        amount: Refund amount (None for full refund)
        reason: Refund reason
        
    Returns:
        Dictionary containing refund details
        
    Examples:
        >>> # Full refund
        >>> result = await refund_payment("txn_abc123")
        >>> # Partial refund
        >>> result = await refund_payment("txn_abc123", amount=50.00)
    """
    # Generate refund ID
    refund_id = f"refund_{uuid4().hex[:12]}"
    
    # Simulate refund processing
    await asyncio.sleep(0.3)
    
    return {
        'status': PaymentStatus.REFUNDED.value,
        'refund_id': refund_id,
        'original_transaction_id': transaction_id,
        'amount': amount,
        'reason': reason,
        'timestamp': datetime.utcnow().isoformat(),
    }


async def verify_payment_status(transaction_id: str) -> Dict[str, any]:
    """
    Verify payment status with gateway.
    
    Args:
        transaction_id: Transaction identifier
        
    Returns:
        Payment status information
    """
    # Simulate gateway status check
    await asyncio.sleep(0.2)
    
    return {
        'transaction_id': transaction_id,
        'status': PaymentStatus.COMPLETED.value,
        'timestamp': datetime.utcnow().isoformat(),
    }
