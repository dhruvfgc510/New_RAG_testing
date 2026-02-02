"""
Structured logging utilities for e-commerce application.

Provides transaction logging with:
- Structured logging format
- Transaction tracking
- Error reporting
- Performance monitoring
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TransactionLogger:
    """
    Transaction logger for tracking e-commerce operations.
    
    Provides structured logging with transaction IDs, timestamps,
    and contextual information.
    """
    
    def __init__(self):
        """Initialize transaction logger."""
        self.logs = []
    
    def _format_log(
        self,
        level: LogLevel,
        message: str,
        transaction_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format log entry with structured data.
        
        Args:
            level: Log level
            message: Log message
            transaction_id: Transaction identifier
            extra: Additional context data
            
        Returns:
            Formatted log entry
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "message": message,
        }
        
        if transaction_id:
            log_entry["transaction_id"] = transaction_id
        
        if extra:
            log_entry["extra"] = extra
        
        return log_entry
    
    def log(
        self,
        level: LogLevel,
        message: str,
        transaction_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log message with structured format.
        
        Args:
            level: Log level
            message: Log message
            transaction_id: Transaction identifier
            extra: Additional context
        """
        log_entry = self._format_log(level, message, transaction_id, extra)
        self.logs.append(log_entry)
        
        # In production, this would write to logging system
        print(json.dumps(log_entry))


# Global logger instance
_logger = TransactionLogger()


def log_transaction(
    transaction_id: str,
    amount: float,
    status: str,
    user_id: Optional[str] = None,
    payment_method: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Log transaction details with structured format.
    
    Args:
        transaction_id: Unique transaction identifier
        amount: Transaction amount
        status: Transaction status (pending, completed, failed)
        user_id: User identifier
        payment_method: Payment method used
        extra: Additional transaction metadata
        
    Examples:
        >>> log_transaction(
        ...     transaction_id="txn_123",
        ...     amount=99.99,
        ...     status="completed",
        ...     user_id="user_123",
        ...     payment_method="credit_card"
        ... )
    """
    context = {
        "amount": amount,
        "status": status,
    }
    
    if user_id:
        context["user_id"] = user_id
    
    if payment_method:
        context["payment_method"] = payment_method
    
    if extra:
        context.update(extra)
    
    _logger.log(
        LogLevel.INFO,
        f"Transaction {status}: {transaction_id}",
        transaction_id=transaction_id,
        extra=context
    )


def log_payment_attempt(
    transaction_id: str,
    amount: float,
    gateway: str,
    attempt_number: int
):
    """
    Log payment gateway attempt.
    
    Args:
        transaction_id: Transaction identifier
        amount: Payment amount
        gateway: Payment gateway name
        attempt_number: Retry attempt number
    """
    _logger.log(
        LogLevel.INFO,
        f"Payment attempt #{attempt_number} via {gateway}",
        transaction_id=transaction_id,
        extra={
            "amount": amount,
            "gateway": gateway,
            "attempt": attempt_number,
        }
    )


def log_payment_success(
    transaction_id: str,
    amount: float,
    gateway: str,
    gateway_transaction_id: str
):
    """
    Log successful payment.
    
    Args:
        transaction_id: Transaction identifier
        amount: Payment amount
        gateway: Payment gateway name
        gateway_transaction_id: Gateway's transaction ID
    """
    _logger.log(
        LogLevel.INFO,
        f"Payment successful via {gateway}",
        transaction_id=transaction_id,
        extra={
            "amount": amount,
            "gateway": gateway,
            "gateway_transaction_id": gateway_transaction_id,
        }
    )


def log_payment_failure(
    transaction_id: str,
    amount: float,
    gateway: str,
    error_code: str,
    error_message: str
):
    """
    Log failed payment attempt.
    
    Args:
        transaction_id: Transaction identifier
        amount: Payment amount
        gateway: Payment gateway name
        error_code: Error code from gateway
        error_message: Error description
    """
    _logger.log(
        LogLevel.ERROR,
        f"Payment failed via {gateway}: {error_message}",
        transaction_id=transaction_id,
        extra={
            "amount": amount,
            "gateway": gateway,
            "error_code": error_code,
            "error_message": error_message,
        }
    )


def log_inventory_change(
    product_id: str,
    quantity_change: int,
    reason: str,
    order_id: Optional[str] = None
):
    """
    Log inventory changes for audit trail.
    
    Args:
        product_id: Product identifier
        quantity_change: Quantity change (positive or negative)
        reason: Reason for change (sale, restock, adjustment, return)
        order_id: Related order ID if applicable
    """
    context = {
        "product_id": product_id,
        "quantity_change": quantity_change,
        "reason": reason,
    }
    
    if order_id:
        context["order_id"] = order_id
    
    _logger.log(
        LogLevel.INFO,
        f"Inventory change: {product_id} ({quantity_change:+d})",
        extra=context
    )


def log_error(
    error_message: str,
    error_type: Optional[str] = None,
    transaction_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Log error with context.
    
    Args:
        error_message: Error description
        error_type: Error type/category
        transaction_id: Related transaction ID
        extra: Additional error context
        
    Examples:
        >>> log_error(
        ...     error_message="Payment gateway timeout",
        ...     error_type="PaymentTimeout",
        ...     transaction_id="txn_123"
        ... )
    """
    context = {}
    
    if error_type:
        context["error_type"] = error_type
    
    if extra:
        context.update(extra)
    
    _logger.log(
        LogLevel.ERROR,
        error_message,
        transaction_id=transaction_id,
        extra=context if context else None
    )


def log_info(
    message: str,
    transaction_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Log informational message.
    
    Args:
        message: Log message
        transaction_id: Related transaction ID
        extra: Additional context
    """
    _logger.log(
        LogLevel.INFO,
        message,
        transaction_id=transaction_id,
        extra=extra
    )


def log_warning(
    message: str,
    transaction_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Log warning message.
    
    Args:
        message: Warning message
        transaction_id: Related transaction ID
        extra: Additional context
    """
    _logger.log(
        LogLevel.WARNING,
        message,
        transaction_id=transaction_id,
        extra=extra
    )


def get_logs() -> list:
    """
    Retrieve all logged entries.
    
    Returns:
        List of log entries
    """
    return _logger.logs.copy()


def clear_logs():
    """Clear all logged entries (for testing)."""
    _logger.logs.clear()
