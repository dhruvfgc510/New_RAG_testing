"""
Configuration settings for e-commerce application.
"""

from .settings import (
    PAYMENT_GATEWAY_URL,
    PAYMENT_TIMEOUT_SECONDS,
    MAX_PAYMENT_RETRIES,
    EMAIL_FROM_ADDRESS,
    EMAIL_SMTP_SERVER,
    TAX_RATE,
    DATABASE_URL,
    REDIS_URL,
)

__all__ = [
    "PAYMENT_GATEWAY_URL",
    "PAYMENT_TIMEOUT_SECONDS",
    "MAX_PAYMENT_RETRIES",
    "EMAIL_FROM_ADDRESS",
    "EMAIL_SMTP_SERVER",
    "TAX_RATE",
    "DATABASE_URL",
    "REDIS_URL",
]

__version__ = "1.0.0"
