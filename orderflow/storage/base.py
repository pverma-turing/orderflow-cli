from abc import ABC, abstractmethod


class Storage(ABC):
    """Base class for storage implementations"""

    @abstractmethod
    def save_order(self, order):
        """Save an order to storage"""
        pass

    @abstractmethod
    def get_orders(self):
        """Retrieve all orders from storage"""
        pass

    @abstractmethod
    def get_order(self, order_id):
        """Retrieve a specific order by ID"""
        pass