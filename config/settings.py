"""
Application configuration settings.

Centralized configuration for all services including:
- Payment gateway settings
- Email service configuration
- Database connections
- Tax rates and business rules
"""

import os
from typing import Final


# =====================================
# Payment Gateway Configuration
# =====================================

PAYMENT_GATEWAY_URL: Final[str] = os.getenv(
    "PAYMENT_GATEWAY_URL",
    "https://api.stripe.com/v1/charges"
)
"""Payment gateway API endpoint URL"""

PAYMENT_TIMEOUT_SECONDS: Final[int] = int(os.getenv("PAYMENT_TIMEOUT_SECONDS", "30"))
"""Maximum time to wait for payment gateway response (seconds)"""

MAX_PAYMENT_RETRIES: Final[int] = int(os.getenv("MAX_PAYMENT_RETRIES", "3"))
"""Maximum number of payment retry attempts"""

PAYMENT_API_KEY: Final[str] = os.getenv("PAYMENT_API_KEY", "sk_test_XXXXXXXXXXXXX")
"""Payment gateway API key (should be loaded from environment)"""


# =====================================
# Email Service Configuration
# =====================================

EMAIL_FROM_ADDRESS: Final[str] = os.getenv(
    "EMAIL_FROM_ADDRESS",
    "noreply@ecommerce-example.com"
)
"""Email sender address"""

EMAIL_SMTP_SERVER: Final[str] = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
"""SMTP server hostname"""

EMAIL_SMTP_PORT: Final[int] = int(os.getenv("EMAIL_SMTP_PORT", "587"))
"""SMTP server port"""

EMAIL_SMTP_USERNAME: Final[str] = os.getenv("EMAIL_SMTP_USERNAME", "")
"""SMTP authentication username"""

EMAIL_SMTP_PASSWORD: Final[str] = os.getenv("EMAIL_SMTP_PASSWORD", "")
"""SMTP authentication password"""


# =====================================
# Tax Configuration
# =====================================

TAX_RATE: Final[float] = float(os.getenv("TAX_RATE", "0.08"))
"""Tax rate (8% by default)"""

TAX_EXEMPT_CATEGORIES: Final[list] = ["food", "books"]
"""Product categories exempt from tax"""


# =====================================
# Database Configuration
# =====================================

DATABASE_URL: Final[str] = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/ecommerce"
)
"""PostgreSQL database connection URL"""

DATABASE_POOL_SIZE: Final[int] = int(os.getenv("DATABASE_POOL_SIZE", "10"))
"""Database connection pool size"""

DATABASE_MAX_OVERFLOW: Final[int] = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
"""Maximum overflow connections"""


# =====================================
# Redis Configuration (Session/Cache)
# =====================================

REDIS_URL: Final[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
"""Redis connection URL"""

REDIS_TTL_SECONDS: Final[int] = int(os.getenv("REDIS_TTL_SECONDS", "3600"))
"""Default Redis key TTL (seconds)"""


# =====================================
# Inventory Configuration
# =====================================

LOW_STOCK_THRESHOLD: Final[int] = int(os.getenv("LOW_STOCK_THRESHOLD", "10"))
"""Threshold for low stock alerts"""

RESERVATION_TIMEOUT_MINUTES: Final[int] = int(os.getenv("RESERVATION_TIMEOUT_MINUTES", "15"))
"""Stock reservation timeout (minutes)"""


# =====================================
# Order Configuration
# =====================================

MAX_ORDER_AMOUNT: Final[float] = float(os.getenv("MAX_ORDER_AMOUNT", "10000.00"))
"""Maximum order amount ($)"""

MIN_ORDER_AMOUNT: Final[float] = float(os.getenv("MIN_ORDER_AMOUNT", "1.00"))
"""Minimum order amount ($)"""

MAX_ITEMS_PER_ORDER: Final[int] = int(os.getenv("MAX_ITEMS_PER_ORDER", "50"))
"""Maximum items per order"""


# =====================================
# Security Configuration
# =====================================

JWT_SECRET_KEY: Final[str] = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
"""JWT secret key for authentication"""

JWT_EXPIRATION_HOURS: Final[int] = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
"""JWT token expiration time (hours)"""

BCRYPT_ROUNDS: Final[int] = int(os.getenv("BCRYPT_ROUNDS", "12"))
"""Bcrypt hashing rounds"""


# =====================================
# API Configuration
# =====================================

API_VERSION: Final[str] = "v1"
"""API version"""

API_BASE_URL: Final[str] = os.getenv("API_BASE_URL", "http://localhost:8000")
"""API base URL"""

API_RATE_LIMIT: Final[int] = int(os.getenv("API_RATE_LIMIT", "100"))
"""API rate limit (requests per minute)"""


# =====================================
# Logging Configuration
# =====================================

LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")
"""Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""

LOG_FORMAT: Final[str] = "json"
"""Log format (json or text)"""


# =====================================
# Feature Flags
# =====================================

ENABLE_EMAIL_NOTIFICATIONS: Final[bool] = os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "true").lower() == "true"
"""Enable email notifications"""

ENABLE_INVENTORY_TRACKING: Final[bool] = os.getenv("ENABLE_INVENTORY_TRACKING", "true").lower() == "true"
"""Enable inventory tracking"""

ENABLE_TAX_CALCULATION: Final[bool] = os.getenv("ENABLE_TAX_CALCULATION", "true").lower() == "true"
"""Enable tax calculation"""


def get_config_summary() -> dict:
    """
    Get summary of current configuration.
    
    Returns:
        Dictionary containing configuration summary
    """
    return {
        "payment": {
            "gateway_url": PAYMENT_GATEWAY_URL,
            "timeout_seconds": PAYMENT_TIMEOUT_SECONDS,
            "max_retries": MAX_PAYMENT_RETRIES,
        },
        "email": {
            "from_address": EMAIL_FROM_ADDRESS,
            "smtp_server": EMAIL_SMTP_SERVER,
        },
        "tax": {
            "rate": TAX_RATE,
            "exempt_categories": TAX_EXEMPT_CATEGORIES,
        },
        "database": {
            "url": DATABASE_URL[:30] + "...",  # Truncated for security
            "pool_size": DATABASE_POOL_SIZE,
        },
        "inventory": {
            "low_stock_threshold": LOW_STOCK_THRESHOLD,
            "reservation_timeout": RESERVATION_TIMEOUT_MINUTES,
        },
    }
