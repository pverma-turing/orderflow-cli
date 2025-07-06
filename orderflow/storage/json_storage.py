import json
import os
from orderflow.models.order import Order
from orderflow.storage.base import Storage


class JsonStorage(Storage):
    """JSON file-based storage implementation"""

    def __init__(self, file_path="orders.json"):
        self.file_path = file_path
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Make sure the storage file exists"""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)

    def _read_all(self):
        """Read all data from storage"""
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def _write_all(self, orders):
        """Write all orders to storage"""
        with open(self.file_path, 'w') as f:
            json.dump(orders, f, indent=2)

    def save_order(self, order):
        """Save an order to storage"""
        orders = self._read_all()

        # Check if order exists - update if it does, add if it doesn't
        for i, existing in enumerate(orders):
            if existing['order_id'] == order.order_id:
                orders[i] = order.to_dict()
                self._write_all(orders)
                return order

        # Add new order
        orders.append(order.to_dict())
        self._write_all(orders)
        return order

    def get_orders(self):
        """Retrieve all orders from storage"""
        orders = self._read_all()
        return [Order.from_dict(order_dict) for order_dict in orders]

    def get_order(self, order_id):
        """Retrieve a specific order by ID"""
        orders = self._read_all()
        for order_dict in orders:
            if order_dict['order_id'] == order_id:
                return Order.from_dict(order_dict)
        return None