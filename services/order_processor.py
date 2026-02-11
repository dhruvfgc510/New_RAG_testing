"""
Self-Contained Order Processing Service.

SCENARIO 3: No Missing Dependencies
- ALL imports are from PR files (INTERNAL only)
- NO imports from main branch (EXTERNAL)
"""

from datetime import datetime
from typing import Dict
from uuid import uuid4

# ============================================
# ALL INTERNAL DEPENDENCIES (FROM PR)
# ============================================
from utils import log_info, log_error
from models import Order, OrderStatus


class OrderProcessingError(Exception):
    """Exception for order processing errors."""
    pass


class OrderProcessor:
    """
    Order processing orchestrator.
    
    This class uses ONLY internal dependencies:
    - log_info, log_error from utils.py (INTERNAL - in PR)
    - Order, OrderStatus from models.py (INTERNAL - in PR)
    
    Everything the LLM needs is in the PR - no missing context!
    """
    
    def __init__(self, user_id: str, order_data: Dict):
        self.user_id = user_id
        self.order_data = order_data
        self.order_id = None
    
    async def process(self) -> Dict:
        """
        Process order through workflow.
        
        All utilities are in the PR:
        - Logging (utils.py)
        - Order model (models.py)
        - Status management (models.py)
        
        Returns:
            Dict with order details
        """
        transaction_id = f"order_{uuid4().hex[:8]}"
        
        log_info(f"Starting order processing", transaction_id)
        
        try:
            # Validate user
            if not self.user_id:
                raise OrderProcessingError("User ID required")
            
            # Validate order data
            if not self.order_data.get("items"):
                raise OrderProcessingError("Order must have items")
            
            if self.order_data.get("total", 0) <= 0:
                raise OrderProcessingError("Order total must be positive")
            
            # Create order ID
            self.order_id = f"order_{uuid4().hex[:12]}"
            
            # Create order (uses Order model from models.py - PR)
            order = Order(
                order_id=self.order_id,
                user_id=self.user_id,
                items=self.order_data["items"],
                total=self.order_data["total"],
                status=OrderStatus.COMPLETED
            )
            
            log_info(f"Order created: {self.order_id}", transaction_id)
            
            return {
                "success": True,
                "order_id": self.order_id,
                "status": "completed",
                "total": self.order_data["total"]
            }
        
        except OrderProcessingError as e:
            log_error(f"Order failed: {str(e)}", transaction_id)
            raise
        
        except Exception as e:
            log_error(f"Unexpected error: {str(e)}", transaction_id)
            raise OrderProcessingError(f"Order processing failed: {str(e)}")
