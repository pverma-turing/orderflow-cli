import argparse
from .base import Command


class DeleteCommand(Command):
    """Command to delete orders from the system."""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        """Add command-specific arguments to parser."""
        # Create a group for identification options
        id_group = parser.add_argument_group("order identification options (at least one required)")

        id_group.add_argument(
            "--order-id",
            type=str,
            help="ID of the order to delete"
        )
        id_group.add_argument(
            "--customer-name",
            type=str,
            help="Name of the customer (use with --order-time)"
        )
        id_group.add_argument(
            "--order-time",
            type=str,
            help="Time of the order (use with --customer-name)"
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation and force deletion"
        )

    def execute(self, args):
        """Execute the delete operation."""
        try:
            # Check for valid identification method
            using_id = args.order_id is not None
            using_customer_time = args.customer_name is not None and args.order_time is not None

            if not using_id and not using_customer_time:
                print("Error: You must provide either --order-id OR both --customer-name and --order-time.")
                return False

            # Check for ambiguous identification
            if using_id and using_customer_time:
                print("Warning: Both --order-id and customer/time provided. Using --order-id for lookup.")

            # Find the order
            if using_id:
                order = self.storage.get_order(args.order_id)
                if not order:
                    print(f"Error: Order with ID '{args.order_id}' not found.")
                    return False
                order_id = args.order_id
            else:  # using customer name and time
                matching_orders = self.storage.find_orders_by_customer_and_time(
                    args.customer_name, args.order_time
                )

                if not matching_orders:
                    print(f"Error: No orders found for customer '{args.customer_name}' at time '{args.order_time}'.")
                    return False

                if len(matching_orders) > 1:
                    print(
                        f"Error: Multiple orders found for customer '{args.customer_name}' at time '{args.order_time}'.")
                    print("Please use --order-id to specify which order to delete.")
                    print("Matching order IDs:")
                    for order in matching_orders:
                        print(f"  - {order.order_id} (status: {order.status}, total: ${order.order_total:.2f})")
                    return False

                order = matching_orders[0]
                order_id = order.order_id

            # Get confirmation unless --force is used
            if not args.force:
                # Display some order details to help confirm it's the right order
                print(f"Order #{order_id}:")
                print(f"  Customer: {order.customer_name}")
                print(f"  Time: {order.order_time}")
                print(f"  Status: {order.status}")
                print(f"  Total: ${order.order_total:.2f}")

                confirmation = input(f"\nAre you sure you want to delete order #{order_id}? (y/n): ")
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