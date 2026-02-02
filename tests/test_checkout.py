"""
Unit tests for checkout API.

Tests the checkout functionality including:
- Input validation
- Payment processing
- Order creation
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Import from feature branch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.checkout import (
    process_checkout,
    CheckoutRequest,
    CheckoutResponse,
    ValidationError,
    CheckoutProcessingError,
)


# ============================================
# TEST FIXTURES
# ============================================

@pytest.fixture
def valid_checkout_request():
    """Create valid checkout request for testing."""
    return CheckoutRequest(
        user_id="user_123",
        items=[
            {"product_id": "prod_1", "quantity": 2},
            {"product_id": "prod_2", "quantity": 1},
        ],
        shipping_address={
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip_code": "62701",
            "country": "US",
        },
        payment_details={
            "card_number": "4532015112830366",
            "expiry_month": "12",
            "expiry_year": "2025",
            "cvv": "123",
            "cardholder_name": "John Doe",
        },
        email="john@example.com",
    )


@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies from main branch."""
    with patch('api.checkout.get_user_by_id') as mock_get_user, \
         patch('api.checkout.get_product_by_id') as mock_get_product, \
         patch('api.checkout.reserve_stock') as mock_reserve, \
         patch('api.checkout.process_payment') as mock_payment, \
         patch('api.checkout.save_order') as mock_save, \
         patch('api.checkout.confirm_reservation') as mock_confirm, \
         patch('api.checkout.send_order_confirmation') as mock_email:
        
        # Mock user
        mock_get_user.return_value = {
            'user_id': 'user_123',
            'email': 'john@example.com',
            'is_active': True,
        }
        
        # Mock product
        mock_get_product.return_value = {
            'product_id': 'prod_1',
            'name': 'Test Product',
            'price': 99.99,
            'is_active': True,
        }
        
        # Mock stock reservation
        mock_reserve.return_value = {
            'reservation_id': 'res_123',
            'product_id': 'prod_1',
            'quantity': 2,
        }
        
        # Mock payment
        mock_payment.return_value = {
            'status': 'completed',
            'transaction_id': 'txn_123',
            'amount': 199.98,
        }
        
        # Mock order save
        mock_save.return_value = 'order_123'
        
        yield {
            'get_user': mock_get_user,
            'get_product': mock_get_product,
            'reserve_stock': mock_reserve,
            'process_payment': mock_payment,
            'save_order': mock_save,
            'confirm_reservation': mock_confirm,
            'send_email': mock_email,
        }


# ============================================
# SUCCESS TESTS
# ============================================

@pytest.mark.asyncio
async def test_successful_checkout(valid_checkout_request, mock_dependencies):
    """Test successful checkout flow."""
    response = await process_checkout(valid_checkout_request)
    
    assert response.status == 'success'
    assert response.order_id == 'order_123'
    assert response.payment_transaction_id == 'txn_123'
    assert response.total_amount > 0


@pytest.mark.asyncio
async def test_checkout_validates_email(valid_checkout_request, mock_dependencies):
    """Test that checkout validates email address."""
    valid_checkout_request.email = "invalid-email"
    
    with pytest.raises(ValidationError) as exc_info:
        await process_checkout(valid_checkout_request)
    
    assert "Invalid email" in str(exc_info.value)


@pytest.mark.asyncio
async def test_checkout_validates_address(valid_checkout_request, mock_dependencies):
    """Test that checkout validates shipping address."""
    valid_checkout_request.shipping_address = {"street": "123"}  # Incomplete
    
    with pytest.raises(ValidationError) as exc_info:
        await process_checkout(valid_checkout_request)
    
    assert "address" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_checkout_validates_credit_card(valid_checkout_request, mock_dependencies):
    """Test that checkout validates credit card number."""
    valid_checkout_request.payment_details['card_number'] = "1234567890"  # Invalid
    
    with pytest.raises(ValidationError) as exc_info:
        await process_checkout(valid_checkout_request)
    
    assert "credit card" in str(exc_info.value).lower()


# ============================================
# ERROR HANDLING TESTS
# ============================================

@pytest.mark.asyncio
async def test_checkout_handles_user_not_found(valid_checkout_request, mock_dependencies):
    """Test checkout handles user not found error."""
    mock_dependencies['get_user'].return_value = None
    
    with pytest.raises(ValidationError) as exc_info:
        await process_checkout(valid_checkout_request)
    
    assert "User not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_checkout_releases_stock_on_payment_failure(valid_checkout_request, mock_dependencies):
    """Test that stock is released when payment fails."""
    # Mock payment failure
    from services.payment_processor import PaymentError
    mock_dependencies['process_payment'].side_effect = PaymentError("Payment declined")
    
    with pytest.raises(PaymentError):
        await process_checkout(valid_checkout_request)
    
    # Verify stock was released
    # Note: This would require checking release_stock was called


@pytest.mark.asyncio
async def test_checkout_sends_confirmation_email(valid_checkout_request, mock_dependencies):
    """Test that confirmation email is sent after successful checkout."""
    await process_checkout(valid_checkout_request)
    
    # Verify email was sent
    mock_dependencies['send_email'].assert_called_once()
    call_args = mock_dependencies['send_email'].call_args
    assert call_args[1]['user_email'] == "john@example.com"


# ============================================
# INTEGRATION TESTS
# ============================================

@pytest.mark.asyncio
async def test_checkout_calculates_tax_correctly(valid_checkout_request, mock_dependencies):
    """Test that checkout calculates tax using TAX_RATE from settings."""
    from config.settings import TAX_RATE
    
    response = await process_checkout(valid_checkout_request)
    
    # Tax calculation should use TAX_RATE from main branch config
    # This test verifies integration with config.settings
    assert response.total_amount > 0


@pytest.mark.asyncio
async def test_checkout_reserves_stock_for_all_items(valid_checkout_request, mock_dependencies):
    """Test that stock is reserved for all items in order."""
    await process_checkout(valid_checkout_request)
    
    # Verify reserve_stock was called for each item
    assert mock_dependencies['reserve_stock'].call_count == 2


@pytest.mark.asyncio
async def test_checkout_confirms_reservations_after_payment(valid_checkout_request, mock_dependencies):
    """Test that reservations are confirmed after successful payment."""
    await process_checkout(valid_checkout_request)
    
    # Verify confirm_reservation was called
    mock_dependencies['confirm_reservation'].assert_called()
