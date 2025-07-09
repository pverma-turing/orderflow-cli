import argparse
import re

from tabulate import tabulate

from .base import Command


class DeleteCommand(Command):
    """Command to delete orders from the system."""
    # Add a class-level constant for the expected datetime format
    DATETIME_FORMAT = "%Y-%m-%d %H:%M"
    DATETIME_PATTERN = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"  # Regex to validate format

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
            help=f"Time of the order in format {self.DATETIME_FORMAT} (use with --customer-name)"
        )
        id_group.add_argument(
            "--tag",
            type=str,
            help="Delete all orders with this tag"
        )

        # Add operation mode flags
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation and force deletion"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate deletion without actually removing any orders"
        )

    def _validate_datetime_format(self, datetime_str):
        """
        Validate that the datetime string follows the expected format.

        Args:
            datetime_str (str): The datetime string to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not datetime_str:
            return False

        # Use regex to strictly check the format
        return bool(re.match(self.DATETIME_PATTERN, datetime_str))

    def _is_valid_order(self, order):
        """
        Check if an order is valid for deletion (has required fields).

        Args:
            order: The order object to validate

        Returns:
            bool: True if the order is valid, False otherwise
        """
        # Check for essential fields
        if not hasattr(order, 'order_id') or not order.order_id:
            return False

        # For tag-based deletion, ensure tags exist (other modes don't need this check)
        if hasattr(order, 'tags') and order.tags is None:
            return False

        return True

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

    def _format_order_summary(self, order):
        """
        Create a concise summary of an order for deletion feedback.

        Args:
            order: The order object

        Returns:
            str: A formatted summary string
        """
        # Safe getattr to handle potentially missing attributes
        order_id = getattr(order, 'order_id', 'Unknown ID')
        customer_name = getattr(order, 'customer_name', 'Unknown customer')
        order_time = getattr(order, 'order_time', 'Unknown time')
        status = getattr(order, 'status', 'Unknown status')

        # Format total with currency symbol
        if hasattr(order, 'order_total'):
            total = f"₹{order.order_total:.2f}"
        else:
            total = "₹0.00"

        # Count dishes
        dish_count = 0
        if hasattr(order, 'dishes') and order.dishes:
            dish_count = len(order.dishes)

        # Build the summary string
        summary = f"[{order_id}] {customer_name} – {total} – {status} – {dish_count} items at {order_time}"

        return summary

    def _format_order_preview(self, order):
        """Create a formatted preview of the order in tabular format."""
        # Create a table with key order details
        headers = ["Order ID", "Customer", "Time", "Status", "Total", "Dishes"]

        # Format dishes for display
        formatted_dishes = self._format_dishes(order.dishes)

        # Format monetary value
        formatted_total = f"₹{order.order_total:.2f}"

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
            # Skip invalid orders in the summary
            if not self._is_valid_order(order):
                continue

            rows.append([
                order.order_id,
                order.customer_name if hasattr(order, 'customer_name') else 'N/A',
                order.order_time if hasattr(order, 'order_time') else 'N/A',
                order.status if hasattr(order, 'status') else 'N/A',
                f"₹{order.order_total:.2f}" if hasattr(order, 'order_total') else 'N/A'
            ])

        # Add a summary row if there are more orders
        if len(orders) > 10:
            rows.append(["...", f"+ {len(orders) - 10} more orders", "", "", ""])

        return tabulate(rows, headers=headers, tablefmt="grid")

    def execute(self, args, storage):
        """Execute the delete operation."""
        try:
            # Check if we're using tag-based deletion
            if args.tag:
                return self._handle_tag_deletion(args.tag, args.force, args.dry_run, storage)

            # Early validation of order-time format if provided
            if args.order_time is not None:
                if not self._validate_datetime_format(args.order_time):
                    print(f"Error: Invalid order time format. Please use {self.DATETIME_FORMAT}")
                    return False

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
                order = storage.get_order(args.order_id)
                if not order:
                    print(f"Error: Order with ID '{args.order_id}' not found.")
                    return False
            else:  # using customer name and time
                matching_orders = storage.find_orders_by_customer_and_time(
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

            # Display order preview unless --force is used
            if not args.force:
                # Add dry-run indicator to the preview title if applicable
                title_prefix = "Dry Run - " if args.dry_run else ""
                print(f"\n{title_prefix}Order to Delete:")
                print(self._format_order_preview(order))

                # Request confirmation
                action_verb = "simulate deleting" if args.dry_run else "delete"
                confirmation = input(f"\nAre you sure you want to {action_verb} this order? (y/n): ")
                if confirmation.lower() not in ["y", "yes"]:
                    print("Operation cancelled.")
                    return False

            # Handle dry run mode
            if args.dry_run:
                print(f"Dry run: Order would have been deleted:")
                print(f"  Deleted order: {self._format_order_summary(order)}")
                return True

            # Store order_id before deletion (to use in success message)
            order_id = order.order_id
            order_summary = self._format_order_summary(order)

            # Perform actual deletion
            success = storage.delete_order(order_id)

            if success:
                print(f"Deleted order: {order_summary}")
                return True
            else:
                print(f"Error: Failed to delete order #{order_id}.")
                return False

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False

    def _handle_tag_deletion(self, tag, force, dry_run, storage):
        """Handle deletion of orders by tag."""
        try:
            # Find all orders with this tag
            matching_orders = storage.find_orders_by_tag(tag)

            # Check if any orders match the tag
            if not matching_orders:
                print(f"No orders found with tag '{tag}'.")
                return False

            # Count all orders and valid orders
            total_matched = len(matching_orders)
            valid_orders = [order for order in matching_orders if self._is_valid_order(order)]
            valid_count = len(valid_orders)
            invalid_count = total_matched - valid_count

            # Early warning if there are invalid orders
            if invalid_count > 0:
                print(f"Warning: Found {invalid_count} malformed order(s) with missing or invalid fields.")
                print(f"These orders will be skipped during the deletion process.")

            # If no valid orders, exit early
            if valid_count == 0:
                print(f"No valid orders to delete with tag '{tag}'.")
                return False

            # Display a summary of the orders to be deleted
            if not force:
                # Add dry-run indicator to the title if applicable
                title_prefix = "Dry Run - " if dry_run else ""
                print(f"\n{title_prefix}Found {valid_count} valid order(s) with tag '{tag}':")
                print(self._preview_orders_summary(valid_orders))

                # Request confirmation
                action_verb = "simulate deleting" if dry_run else "delete"
                confirmation = input(f"\nAre you sure you want to {action_verb} {valid_count} order(s)? (y/n): ")
                if confirmation.lower() not in ["y", "yes"]:
                    print("Operation cancelled.")
                    return False

            # Handle dry run mode
            if dry_run:
                print(f"\nDry run: The following orders would have been deleted:")
                for order in matching_orders:
                    if self._is_valid_order(order):
                        print(f"  Deleted order: {self._format_order_summary(order)}")
                    else:
                        print(f"  Skipped malformed order: {getattr(order, 'order_id', 'Unknown ID')}")

                if invalid_count > 0:
                    print(
                        f"\n{valid_count} order(s) would have been deleted, {invalid_count} order(s) would have been skipped.")
                else:
                    print(f"\n{valid_count} order(s) would have been deleted.")
                return True

            # Perform actual deletion
            deleted_count = 0
            skipped_count = 0
            print("\nDeleting orders...")

            for order in matching_orders:
                # Skip invalid orders with a warning
                if not self._is_valid_order(order):
                    print(f"  Skipped malformed order: {getattr(order, 'order_id', 'Unknown ID')}")
                    skipped_count += 1
                    continue

                # Format the order summary before deletion
                order_summary = self._format_order_summary(order)

                # Try to delete the valid order
                if storage.delete_order(order.order_id):
                    print(f"  Deleted order: {order_summary}")
                    deleted_count += 1
                else:
                    print(f"  Failed to delete: [{order.order_id}]")
                    skipped_count += 1

            # Report results
            print("\nSummary:")
            if deleted_count > 0:
                if skipped_count > 0:
                    print(f"✓ Successfully deleted {deleted_count} order(s) with tag '{tag}'.")
                    print(f"⚠ Skipped {skipped_count} order(s) due to errors or invalid data.")
                else:
                    print(f"✓ Successfully deleted all {deleted_count} order(s) with tag '{tag}'.")
                return True
            else:
                print(f"✘ Failed to delete any orders with tag '{tag}'.")
                if skipped_count > 0:
                    print(f"⚠ All {skipped_count} order(s) were skipped due to errors or invalid data.")
                return False

        except Exception as e:
            print(f"An unexpected error occurred while processing orders by tag: {e}")
            return False