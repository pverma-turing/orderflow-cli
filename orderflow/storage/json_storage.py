import json
import os
import sys
from orderflow.models.order import Order
from orderflow.storage.base import Storage


class JsonStorage(Storage):
    """JSON file-based storage implementation with robust error handling"""

    def __init__(self, file_path="orders.json"):
        self.file_path = file_path
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Make sure the storage file exists and is properly formatted"""
        if not os.path.exists(self.file_path):
            # Create a new empty storage file
            try:
                with open(self.file_path, 'w') as f:
                    json.dump([], f)
                print(f"Created new storage file at {self.file_path}")
            except (PermissionError, IOError) as e:
                print(f"Error: Cannot create storage file at {self.file_path}")
                print(f"Details: {str(e)}")
                sys.exit(1)
        else:
            # Validate existing file
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    # Ensure it's a list
                    if not isinstance(data, list):
                        raise ValueError("Storage file contains invalid format (expected a list)")
            except json.JSONDecodeError:
                # File exists but is not valid JSON
                print(f"Warning: Storage file {self.file_path} is malformed.")
                backup_path = f"{self.file_path}.bak"
                print(f"Creating backup at {backup_path} and initializing new file.")
                try:
                    # Create backup of bad file
                    if os.path.getsize(self.file_path) > 0:
                        with open(self.file_path, 'r') as src, open(backup_path, 'w') as dst:
                            dst.write(src.read())
                    # Reset the file
                    with open(self.file_path, 'w') as f:
                        json.dump([], f)
                except (PermissionError, IOError) as e:
                    print(f"Error: Failed to fix storage file.")
                    print(f"Details: {str(e)}")
                    sys.exit(1)
            except (PermissionError, IOError) as e:
                print(f"Error: Cannot access storage file at {self.file_path}")
                print(f"Details: {str(e)}")
                sys.exit(1)
            except Exception as e:
                print(f"Error: Unexpected issue with storage file: {str(e)}")
                sys.exit(1)

    def _read_all(self):
        """Read all data from storage with error handling"""
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                # Validate that storage contains a list
                if not isinstance(data, list):
                    print(f"Warning: Storage file {self.file_path} has invalid format.")
                    return []
                return data
        except json.JSONDecodeError:
            print(f"Error: Storage file {self.file_path} contains invalid JSON.")
            print("Please fix the file or delete it to create a new one.")
            return []
        except (PermissionError, IOError) as e:
            print(f"Error: Cannot read storage file at {self.file_path}")
            print(f"Details: {str(e)}")
            return []
        except Exception as e:
            print(f"Error: Unexpected issue reading storage: {str(e)}")
            return []

    def _write_all(self, orders):
        """Write all orders to storage with error handling"""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(orders, f, indent=2)
            return True
        except (PermissionError, IOError) as e:
            print(f"Error: Cannot write to storage file at {self.file_path}")
            print(f"Details: {str(e)}")
            return False
        except Exception as e:
            print(f"Error: Unexpected issue writing to storage: {str(e)}")
            return False

    def save_order(self, order):
        """Save an order to storage with error handling"""
        orders = self._read_all()

        if orders is None:
            print("Error: Could not read existing orders.")
            return None

        # Convert order to dict for storage
        order_dict = order.to_dict()

        # Check if order exists - update if it does, add if it doesn't
        updated = False
        for i, existing in enumerate(orders):
            if existing.get('order_id') == order.order_id:
                orders[i] = order_dict
                updated = True
                break

        # Add new order if not updated
        if not updated:
            orders.append(order_dict)

        # Write back to storage
        if self._write_all(orders):
            return order
        else:
            print("Warning: Failed to save order to storage.")
            return None

    def get_orders(self):
        """Retrieve all orders from storage with error handling and format conversion"""
        orders_data = self._read_all()
        orders = []

        for i, order_dict in enumerate(orders_data):
            try:
                # Handle old format conversion
                if 'dish_names' in order_dict and 'dishes' not in order_dict:
                    # Convert old dish_names format to new dishes format for downstream consistency
                    dish_names = order_dict['dish_names']
                    # No need to modify order_dict here - the Order class handles the conversion

                # Create order object
                order = Order.from_dict(order_dict)
                orders.append(order)
            except ValueError as e:
                print(f"Warning: Skipping invalid order at index {i}: {str(e)}")
            except Exception as e:
                print(f"Warning: Error parsing order at index {i}: {str(e)}")

        return orders

    def get_order(self, order_id):
        """Retrieve a specific order by ID with error handling"""
        if not order_id:
            print("Error: No order ID provided.")
            return None

        orders_data = self._read_all()

        for order_dict in orders_data:
            if order_dict.get('order_id') == order_id:
                try:
                    return Order.from_dict(order_dict)
                except ValueError as e:
                    print(f"Error: Invalid order data for ID {order_id}: {str(e)}")
                    return None
                except Exception as e:
                    print(f"Error: Unexpected issue with order ID {order_id}: {str(e)}")
                    return None

        print(f"Order with ID '{order_id}' not found.")
        return None

    def get_orders_by_ids(self, order_ids):
        """Retrieve multiple orders by their IDs efficiently"""
        if not order_ids:
            return []

        # Create a dictionary for faster lookup by ID
        orders_dict = {}

        # Get all orders data
        orders_data = self._read_all()

        # First pass: Build a dictionary of orders by ID
        for order_data in orders_data:
            order_id = order_data.get('order_id')
            if order_id in order_ids:
                try:
                    orders_dict[order_id] = Order.from_dict(order_data)
                except (ValueError, Exception) as e:
                    print(f"Warning: Error parsing order with ID {order_id}: {str(e)}")

        # Return orders in the same order as the input IDs
        return [orders_dict.get(order_id) for order_id in order_ids]

    def save_orders_batch(self, orders):
        """Save multiple orders in a single operation for efficiency"""
        if not orders:
            return []

        # Read all existing orders
        all_orders_data = self._read_all()
        all_orders_dict = {order_data.get('order_id'): order_data for order_data in all_orders_data}

        # Update or add each order
        saved_orders = []
        for order in orders:
            order_dict = order.to_dict()
            all_orders_dict[order.order_id] = order_dict
            saved_orders.append(order)

        # Write back all orders
        if self._write_all(list(all_orders_dict.values())):
            return saved_orders

        return []

    def delete_order(self, order_id):
        """
        Delete an order from storage by its ID.

        Args:
            order_id (str): The ID of the order to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            # Load all orders
            orders = self.get_orders()

            # Find order index
            order_index = None
            for i, order in enumerate(orders):
                if order.order_id == order_id:
                    order_index = i
                    break

            # If order not found, return False
            if order_index is None:
                return False

            # Remove the order
            orders.pop(order_index)

            remaining_orders = []
            for order in orders:
                order_dict = order.to_dict()
                remaining_orders.append(order_dict)


            # Persist the change
            self._write_all(remaining_orders)

            return True
        except Exception as e:
            # Log the error if logging is set up
            # self.logger.error(f"Error deleting order {order_id}: {e}")
            return False