"""
Email notification service for e-commerce application.

Provides email notifications for:
- Order confirmations
- Shipping notifications
- Payment receipts
- Account notifications
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from utils.logger import log_info, log_error
from utils.validator import validate_email
from config.settings import EMAIL_FROM_ADDRESS, EMAIL_SMTP_SERVER


class EmailError(Exception):
    """Base exception for email errors."""
    pass


class InvalidEmailError(EmailError):
    """Exception for invalid email addresses."""
    pass


async def send_order_confirmation(
    user_email: str,
    order_details: Dict[str, any]
) -> Dict[str, any]:
    """
    Send order confirmation email to customer.
    
    Args:
        user_email: Customer email address
        order_details: Dictionary containing:
            - order_id: Order identifier
            - products: List of ordered products
            - total_amount: Total order amount
            - shipping_address: Shipping address
            - estimated_delivery: Estimated delivery date
            
    Returns:
        Dictionary containing:
            - email_id: Email message ID
            - status: Send status
            - timestamp: Send timestamp
            
    Raises:
        InvalidEmailError: If email address is invalid
        EmailError: If email sending fails
        
    Examples:
        >>> order = {
        ...     "order_id": "order_123",
        ...     "products": [{"name": "Laptop", "quantity": 1, "price": 999.99}],
        ...     "total_amount": 999.99,
        ...     "shipping_address": {...},
        ...     "estimated_delivery": "2024-01-15"
        ... }
        >>> result = await send_order_confirmation("user@example.com", order)
    """
    # Validate email address
    is_valid, error_message = validate_email(user_email)
    if not is_valid:
        raise InvalidEmailError(f"Invalid email address: {error_message}")
    
    # Validate order details
    required_fields = ['order_id', 'products', 'total_amount']
    missing_fields = [field for field in required_fields if field not in order_details]
    
    if missing_fields:
        raise ValueError(f"Missing order details: {', '.join(missing_fields)}")
    
    # Generate email ID
    email_id = f"email_{uuid4().hex[:12]}"
    
    # Build email content
    email_content = _build_order_confirmation_email(order_details)
    
    # Log email attempt
    log_info(
        message=f"Sending order confirmation email to {user_email}",
        extra={
            'email_id': email_id,
            'order_id': order_details['order_id'],
            'recipient': user_email,
        }
    )
    
    try:
        # Send email via SMTP
        await _send_email(
            to_address=user_email,
            subject=f"Order Confirmation - {order_details['order_id']}",
            body=email_content,
            email_id=email_id
        )
        
        log_info(
            message=f"Order confirmation email sent successfully",
            extra={
                'email_id': email_id,
                'order_id': order_details['order_id'],
            }
        )
        
        return {
            'email_id': email_id,
            'status': 'sent',
            'recipient': user_email,
            'order_id': order_details['order_id'],
            'timestamp': datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        log_error(
            error_message=f"Failed to send order confirmation email: {str(e)}",
            error_type="EmailError",
            extra={
                'email_id': email_id,
                'order_id': order_details['order_id'],
                'recipient': user_email,
            }
        )
        raise EmailError(f"Failed to send email: {str(e)}")


def _build_order_confirmation_email(order_details: Dict[str, any]) -> str:
    """
    Build order confirmation email content.
    
    Args:
        order_details: Order information
        
    Returns:
        Email body content (HTML)
    """
    products_html = ""
    for product in order_details['products']:
        products_html += f"""
        <tr>
            <td>{product.get('name', 'Unknown')}</td>
            <td>{product.get('quantity', 1)}</td>
            <td>${product.get('price', 0):.2f}</td>
        </tr>
        """
    
    email_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; }}
            .content {{ padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .total {{ font-weight: bold; font-size: 18px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Order Confirmation</h1>
        </div>
        <div class="content">
            <p>Thank you for your order!</p>
            <p><strong>Order ID:</strong> {order_details['order_id']}</p>
            
            <h2>Order Details</h2>
            <table>
                <tr>
                    <th>Product</th>
                    <th>Quantity</th>
                    <th>Price</th>
                </tr>
                {products_html}
            </table>
            
            <p class="total">Total: ${order_details['total_amount']:.2f}</p>
            
            <p>Your order will be shipped to:</p>
            <p>{_format_address(order_details.get('shipping_address', {}))}</p>
            
            <p>Estimated delivery: {order_details.get('estimated_delivery', 'TBD')}</p>
        </div>
    </body>
    </html>
    """
    
    return email_body


async def send_shipping_notification(
    user_email: str,
    tracking_info: Dict[str, any]
) -> Dict[str, any]:
    """
    Send shipping notification with tracking information.
    
    Args:
        user_email: Customer email address
        tracking_info: Dictionary containing:
            - order_id: Order identifier
            - tracking_number: Shipment tracking number
            - carrier: Shipping carrier
            - estimated_delivery: Estimated delivery date
            
    Returns:
        Dictionary with email send status
        
    Examples:
        >>> tracking = {
        ...     "order_id": "order_123",
        ...     "tracking_number": "1Z999AA10123456784",
        ...     "carrier": "UPS",
        ...     "estimated_delivery": "2024-01-20"
        ... }
        >>> result = await send_shipping_notification("user@example.com", tracking)
    """
    # Validate email
    is_valid, error_message = validate_email(user_email)
    if not is_valid:
        raise InvalidEmailError(f"Invalid email address: {error_message}")
    
    # Generate email ID
    email_id = f"email_{uuid4().hex[:12]}"
    
    # Build email content
    email_content = f"""
    <html>
    <body>
        <h1>Your Order Has Shipped!</h1>
        <p>Order ID: {tracking_info['order_id']}</p>
        <p>Tracking Number: {tracking_info['tracking_number']}</p>
        <p>Carrier: {tracking_info['carrier']}</p>
        <p>Estimated Delivery: {tracking_info['estimated_delivery']}</p>
    </body>
    </html>
    """
    
    # Send email
    await _send_email(
        to_address=user_email,
        subject=f"Your Order Has Shipped - {tracking_info['order_id']}",
        body=email_content,
        email_id=email_id
    )
    
    return {
        'email_id': email_id,
        'status': 'sent',
        'timestamp': datetime.utcnow().isoformat(),
    }


async def _send_email(
    to_address: str,
    subject: str,
    body: str,
    email_id: str
) -> None:
    """
    Send email via SMTP server.
    
    Args:
        to_address: Recipient email
        subject: Email subject
        body: Email body (HTML)
        email_id: Email message ID
    """
    # In production, this would use aiosmtplib or similar:
    # async with aiosmtplib.SMTP(
    #     hostname=EMAIL_SMTP_SERVER,
    #     port=587,
    #     use_tls=True
    # ) as smtp:
    #     message = MIMEMultipart()
    #     message['From'] = EMAIL_FROM_ADDRESS
    #     message['To'] = to_address
    #     message['Subject'] = subject
    #     message.attach(MIMEText(body, 'html'))
    #     await smtp.send_message(message)
    
    # Simulate email sending delay
    await asyncio.sleep(0.3)


def _format_address(address: Dict[str, str]) -> str:
    """
    Format address for email display.
    
    Args:
        address: Address dictionary
        
    Returns:
        Formatted address string
    """
    if not address:
        return "Address not provided"
    
    return f"""
    {address.get('street', '')}<br>
    {address.get('city', '')}, {address.get('state', '')} {address.get('zip_code', '')}<br>
    {address.get('country', '')}
    """
