import argparse
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
        order_id = args.order_id

        try:
            # First, check if the order exists
            order = self.storage.get_order(order_id)
            if not order:
                print(f"Error: Order with ID '{order_id}' not found.")
                return False

            # Get confirmation unless --force is used
            if not args.force:
                confirmation = input(f"Are you sure you want to delete order #{order_id}? (y/n): ")
                if confirmation.lower() not in ["y", "yes"]:
                    print("Deletion cancelled.")
                    return False

            # Delete the order using storage
            success = self.storage.delete_order(order_id)

            if success:
                print(f"Order #{order_id} successfully deleted.")
                return True
            else:
                print(f"Error: Failed to delete order #{order_id}.")
                return False

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False