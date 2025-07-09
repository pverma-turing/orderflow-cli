import argparse

from tabulate import tabulate

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
        id_group.add_argument(
            "--tag",
            type=str,
            help="Delete all orders with this tag"
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation and force deletion"
        )

    def _format_dishes(self, dishes):
        """Format dish list for display."""
        if not dishes:
            return "None"

        dish_strings = []
        for dish in dishes[:3]:  # Display up to 3 dishes to keep the output clean
            dish_strings.append(dish)

        if len(dishes) > 3:
            dish_strings.append(f"...and {len(dishes) - 3} more")

        return "\n".join(dish_strings)

    def _format_order_preview(self, order):
        """Create a formatted preview of the order in tabular format."""
        # Create a table with key order details
        headers = ["Order ID", "Customer", "Time", "Status", "Total", "Dishes"]

        # Format dishes for display
        formatted_dishes = self._format_dishes(order.dishes)

        # Format monetary value
        formatted_total = f"${order.order_total:.2f}"

        # Create a single row with the order details
        row = [
            order.order_id,
            order.customer_name,
            order.order_time,
            order.status,
            formatted_total,
            formatted_dishes
        ]

        # Generate table using tabulate with grid format
        table = tabulate([row], headers=headers, tablefmt="grid")

        return table

    def _preview_orders_summary(self, orders):
        """Create a summary table of multiple orders."""
        if not orders:
            return "No orders found."

        # Create a table with summary information
        headers = ["Order ID", "Customer", "Time", "Status", "Total"]
        rows = []

        for order in orders[:10]:  # Limit to 10 orders in the preview
            rows.append([
                order.order_id,
                order.customer_name,
                order.order_time,
                order.status,
                f"${order.order_total:.2f}"
            ])

        # Add a summary row if there are more orders
        if len(orders) > 10:
            rows.append(["...", f"+ {len(orders) - 10} more orders", "", "", ""])

        return tabulate(rows, headers=headers, tablefmt="grid")

    def execute(self, args):
        """Execute the delete operation."""
        try:
            # Check if we're using tag-based deletion
            if args.tag:
                return self._handle_tag_deletion(args.tag, args.force, self.storage)

            # Regular single-order deletion
            # Check for valid identification method
            using_id = args.order_id is not None
            using_customer_time = args.customer_name is not None and args.order_time is not None

            if not using_id and not using_customer_time:
                print("Error: You must provide either --order-id OR both --customer-name and --order-time, OR --tag.")
                return False

            # Check for ambiguous identification
            if using_id and using_customer_time:
                print("Warning: Both --order-id and customer/time provided. Using --order-id for lookup.")

            # Find the order
            order = None
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
                    print("\nMatching orders:")
                    print(self._preview_orders_summary(matching_orders))
                    return False

                order = matching_orders[0]
                order_id = order.order_id

            # Display order preview unless --force is used
            if not args.force:
                print("\nOrder to Delete:")
                print(self._format_order_preview(order))

                # Request confirmation
                confirmation = input(f"\nAre you sure you want to delete this order? (y/n): ")
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

    def _handle_tag_deletion(self, tag, force, storage):
        """Handle deletion of orders by tag."""
        try:
            # Find all orders with this tag
            matching_orders = storage.find_orders_by_tag(tag)

            # Check if any orders match the tag
            if not matching_orders:
                print(f"No orders found with tag '{tag}'.")
                return False

            order_count = len(matching_orders)

            # Display a summary of the orders to be deleted
            if not force:
                print(f"\nFound {order_count} order(s) with tag '{tag}':")
                print(self._preview_orders_summary(matching_orders))

                # Request confirmation
                confirmation = input(f"\nAre you sure you want to delete {order_count} order(s)? (y/n): ")
                if confirmation.lower() not in ["y", "yes"]:
                    print("Deletion cancelled.")
                    return False

            # Delete all matched orders
            deleted_count = 0
            for order in matching_orders:
                if storage.delete_order(order.order_id):
                    deleted_count += 1

            # Report results
            if deleted_count == order_count:
                print(f"Successfully deleted {deleted_count} order(s) with tag '{tag}'.")
                return True
            elif deleted_count > 0:
                print(f"Partially completed: Deleted {deleted_count} of {order_count} orders with tag '{tag}'.")
                print("Some orders could not be deleted. Please try again or check the system logs.")
                return True
            else:
                print(f"Failed to delete any orders with tag '{tag}'.")
                return False

        except Exception as e:
            print(f"An unexpected error occurred while deleting orders by tag: {e}")
            return False