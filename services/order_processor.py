"""
Simplified Order Processing Service.

SCENARIO 2: Partial/Mixed Dependencies
- Imports NO files from PR (all dependencies are EXTERNAL)
- Imports multiple files from main branch (EXTERNAL)

This demonstrates a service that depends entirely on existing infrastructure.
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

# ============================================
# NO INTERNAL DEPENDENCIES FROM PR
# ============================================

# ============================================
# EXTERNAL DEPENDENCIES (FROM MAIN BRANCH)
# ============================================

# Database utilities
from utils.database import (
    save_order,
    get_user_by_id,
)

# Logging utilities
from utils.logger import (
    log_info,
    log_error,
    log_warning,
)

# Payment service
from services.payment_processor import (
    process_payment,
    PaymentStatus,
)

# Inventory service
from services.inventory_service import (
    reserve_stock,
    confirm_reservation,
)

# Data models
from models.order import Order, OrderStatus
from models.user import User


class OrderProcessingError(Exception):
    """Exception for order processing errors."""
    pass


class OrderProcessor:
    """
    Order processing orchestrator.
    
    This class demonstrates 100% EXTERNAL dependencies:
    - Uses database utils from utils.database (EXTERNAL - main branch)
    - Uses logging from utils.logger (EXTERNAL - main branch)
    - Uses payment processor from services.payment_processor (EXTERNAL - main branch)
    - Uses inventory service from services.inventory_service (EXTERNAL - main branch)
    - Uses Order, User models from models/ (EXTERNAL - main branch)
    
    Without these files, LLM won't understand:
    - How orders are saved to database
    - How payments are processed (retry logic, error handling)
    - How inventory is reserved and confirmed
    - Order model structure and status transitions
    - User validation logic
    """
    
    def __init__(self, user_id: str, order_data: Dict):
        self.user_id = user_id
        self.order_data = order_data
        self.order_id = None
        self.reservations = []
        self.payment_result = None
    
    async def process(self) -> Dict:
        """
        Process order through complete workflow.
        
        Steps:
        1. Validate user (uses get_user_by_id from utils.database)
        2. Reserve inventory (uses reserve_stock from services.inventory_service)
        3. Process payment (uses process_payment from services.payment_processor)
        4. Save order (uses save_order from utils.database)
        5. Confirm reservations (uses confirm_reservation from services.inventory_service)
        
        Returns:
            Dict with order details
        
        Raises:
            OrderProcessingError: If processing fails
        """
        transaction_id = f"order_{uuid4().hex[:8]}"
        
        log_info(
            message=f"Starting order processing",
            transaction_id=transaction_id,
            user_id=self.user_id
        )
        
        try:
            # Step 1: Validate user exists (uses utils.database from main branch)
            user = await get_user_by_id(self.user_id)
            if not user:
                raise OrderProcessingError(f"User {self.user_id} not found")
            
            log_info(
                message="User validated",
                transaction_id=transaction_id,
                user_id=self.user_id
            )
            
            # Step 2: Reserve inventory (uses services.inventory_service from main branch)
            await self._reserve_inventory(transaction_id)
            
            # Step 3: Process payment (uses services.payment_processor from main branch)
            await self._process_payment(transaction_id)
            
            # Step 4: Create order (uses utils.database from main branch)
            await self._create_order(transaction_id)
            
            # Step 5: Confirm reservations (uses services.inventory_service from main branch)
            await self._confirm_reservations(transaction_id)
            
            log_info(
                message="Order processing completed successfully",
                transaction_id=transaction_id,
                order_id=self.order_id
            )
            
            return {
                "success": True,
                "order_id": self.order_id,
                "status": "completed",
                "payment_transaction_id": self.payment_result.get("transaction_id"),
                "total": self.order_data["total"]
            }
        
        except OrderProcessingError as e:
            log_error(
                message=f"Order processing failed: {str(e)}",
                transaction_id=transaction_id
            )
            # Cleanup reservations if any were made
            await self._cleanup_reservations(transaction_id)
            raise
        
        except Exception as e:
            log_error(
                message=f"Unexpected order processing error: {str(e)}",
                transaction_id=transaction_id
            )
            await self._cleanup_reservations(transaction_id)
            raise OrderProcessingError(f"Order processing failed: {str(e)}")
    
    async def _reserve_inventory(self, transaction_id: str):
        """
        Reserve inventory for all items.
        
        Uses reserve_stock from services.inventory_service (main branch).
        """
        log_info(
            message="Reserving inventory",
            transaction_id=transaction_id,
            item_count=len(self.order_data["items"])
        )
        
        for item in self.order_data["items"]:
            # Uses services.inventory_service from main branch
            reservation = await reserve_stock(
                product_id=item.get("product_id"),
                quantity=item.get("quantity", 1)
            )
            self.reservations.append(reservation["reservation_id"])
        
        log_info(
            message=f"Reserved {len(self.reservations)} items",
            transaction_id=transaction_id
        )
    
    async def _process_payment(self, transaction_id: str):
        """
        Process payment for order.
        
        Uses process_payment from services.payment_processor (main branch).
        Without this file, LLM won't know about retry logic, timeout handling, etc.
        """
        log_info(
            message="Processing payment",
            transaction_id=transaction_id,
            amount=self.order_data["total"]
        )
        
        # Uses services.payment_processor from main branch
        # This service has complex retry logic, timeout handling, etc.
        self.payment_result = await process_payment(
            amount=self.order_data["total"],
            payment_method="credit_card",
            user_id=self.user_id
        )
        
        if self.payment_result.get("status") != PaymentStatus.COMPLETED:
            raise OrderProcessingError("Payment failed")
        
        log_info(
            message="Payment processed successfully",
            transaction_id=transaction_id,
            payment_id=self.payment_result.get("transaction_id")
        )
    
    async def _create_order(self, transaction_id: str):
        """
        Create order in database.
        
        Uses save_order from utils.database (main branch).
        """
        log_info(
            message="Creating order",
            transaction_id=transaction_id
        )
        
        order_data = {
            "user_id": self.user_id,
            "items": self.order_data["items"],
            "total": self.order_data["total"],
            "payment_transaction_id": self.payment_result["transaction_id"],
            "status": "completed",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Uses utils.database from main branch
        self.order_id = await save_order(order_data)
        
        log_info(
            message="Order created",
            transaction_id=transaction_id,
            order_id=self.order_id
        )
    
    async def _confirm_reservations(self, transaction_id: str):
        """
        Confirm all inventory reservations.
        
        Uses confirm_reservation from services.inventory_service (main branch).
        """
        log_info(
            message="Confirming reservations",
            transaction_id=transaction_id,
            reservation_count=len(self.reservations)
        )
        
        for reservation_id in self.reservations:
            # Uses services.inventory_service from main branch
            await confirm_reservation(reservation_id)
        
        log_info(
            message="All reservations confirmed",
            transaction_id=transaction_id
        )
    
    async def _cleanup_reservations(self, transaction_id: str):
        """Release any reserved inventory on error."""
        if self.reservations:
            log_warning(
                message="Releasing reservations due to error",
                transaction_id=transaction_id,
                reservation_count=len(self.reservations)
            )
            # Cleanup logic would go here
