import argparse
import json
import os
from pathlib import Path

from .base import Command


class DeleteCommand(Command):
    """Command to delete orders from the system."""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        """Add command-specific arguments to parser."""
        parser.add_argument(
            "--order-id",
            type=str,
            required=True,
            help="ID of the order to delete"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation and force deletion"
        )

    def execute(self, args):
        """Execute the delete operation."""
        # Load all orders from storage
        try:
            orders = self.storage.get_orders()

            # Find the order by ID
            order_id = args.order_id
            found = False
            order_index = None

            for i, order in enumerate(orders):
                if order.order_id == order_id:
                    found = True
                    order_index = i
                    break

            if not found:
                print(f"Error: Order with ID '{order_id}' not found.")
                return

            # Get confirmation unless --force is used
            if not args.force:
                confirmation = input(f"Are you sure you want to delete order #{order_id}? (y/n): ")
                if confirmation.lower() not in ["y", "yes"]:
                    print("Deletion cancelled.")
                    return

            # Delete the order from the list
            deleted_order = orders.pop(order_index)

            # Save the updated order list back to the file
            self.storage.save_orders_batch(orders)
            print(f"Order #{order_id} successfully deleted.")

        except json.JSONDecodeError:
            print("Error: Unable to parse order data. The storage file may be corrupted.")
        except PermissionError:
            print("Error: Permission denied when accessing the storage file.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")