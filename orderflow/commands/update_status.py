import argparse
from orderflow.commands.base import Command
from orderflow.models.order import Order
from tabulate import tabulate


class UpdateStatusCommand(Command):
    """Command to update the status of one or multiple orders"""

    VALID_STATUSES = Order.VALID_STATUSES
    VALID_TRANSITIONS = {
        "new": ["preparing", "canceled"],
        "preparing": ["delivered", "canceled"],
        "delivered": [],  # No further transitions allowed
        "canceled": []  # No further transitions allowed
    }

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        # Parameter group for order identification
        id_group = parser.add_mutually_exclusive_group(required=True)

        # Single order ID (for backward compatibility)
        id_group.add_argument(
            'order_id',
            nargs='?',
            default=None,
            help='ID of the order to update'
        )

        # New bulk update option
        id_group.add_argument(
            '--ids',
            help='Comma-separated list of order IDs for bulk update'
        )

        # Required status parameter
        parser.add_argument(
            '--status',
            choices=self.VALID_STATUSES,
            required=True,
            help=f'New status for the order(s) (choices: {", ".join(self.VALID_STATUSES)})'
        )

        # Add verbose option for detailed output
        parser.add_argument(
            '--verbose',
            '-v',
            action='store_true',
            help='Show detailed information about each updated order'
        )

        # Add examples to epilog
        parser.epilog = """
Examples:
  # Update a single order (positional argument)
  orderflow update-status 12345678-abcd-1234-efgh-123456789abc --status preparing

  # Update a single order with detailed output
  orderflow update-status 12345678-abcd-1234-efgh-123456789abc --status delivered --verbose

  # Bulk update multiple orders
  orderflow update-status --ids "id1,id2,id3" --status preparing

  # Bulk update with detailed information
  orderflow update-status --ids "id1,id2,id3" --status canceled --verbose
"""

    def execute(self, args):
        try:
            # Determine if this is a bulk update or single update
            if args.ids:
                return self._execute_bulk_update(args)
            else:
                return self._execute_single_update(args)

        except ValueError as e:
            print(f"Error: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return None

    def _execute_single_update(self, args):
        """Handle a single order update (backward compatibility)"""
        # Validate order ID
        if not args.order_id:
            print("Error: Order ID is required")
            return None

        # Get the order
        order = self.storage.get_order(args.order_id)

        if not order:
            print(f"Error: Order with ID {args.order_id} not found.")
            return None

        # Update the status
        old_status = order.status
        # Check if transition is valid
        if args.status not in self.VALID_TRANSITIONS[order.status]:
            print(f"  Invalid transition: {order.status} → {args.status}")
            return None

        order.status = args.status

        # Save the updated order
        updated_order = self.storage.save_order(order)

        if updated_order:
            print(f"Order {order.order_id} status updated from '{old_status}' to '{args.status}'")

            # Display additional order details if verbose mode
            if args.verbose:
                print(f"Customer: {order.customer_name}")
                print(f"Dishes: {', '.join(order.dish_names)}")
                print(f"Total: ${order.order_total:.2f}")
                if order.tags:
                    print(f"Tags: {', '.join(order.tags)}")

            return updated_order
        else:
            print("Failed to update order status. Please check the errors above.")
            return None

    def _execute_bulk_update(self, args):
        """Handle bulk update of multiple orders using batch operations"""
        # Parse the comma-separated list of IDs
        order_ids = [order_id.strip() for order_id in args.ids.split(',') if order_id.strip()]

        if not order_ids:
            print("Error: No valid order IDs provided.")
            return None

        # Get all specified orders in a single operation
        orders = self.storage.get_orders_by_ids(order_ids) if hasattr(self.storage, 'get_orders_by_ids') else [
            self.storage.get_order(order_id) for order_id in order_ids
        ]

        # Initialize counters
        successful_updates = 0
        not_found = 0
        failed_updates = 0
        unchanged = 0

        # Track orders to update in batch
        to_update = []
        results_data = []

        # Process orders
        for i, order_id in enumerate(order_ids):
            order = orders[i] if i < len(orders) and orders[i] else None

            if not order:
                not_found += 1
                results_data.append([order_id[:8] + "...", "Not Found", "-", "-"])
                continue

            # Skip orders that are already in the target status
            if order.status == args.status:
                unchanged += 1
                results_data.append([
                    order_id[:8] + "...",
                    "Unchanged",
                    args.status,
                    "Already in target status"
                ])
                continue

            # Store old status for reporting
            old_status = order.status
            # Check if transition is valid
            if args.status not in self.VALID_TRANSITIONS[order.status]:
                print(f"  Invalid transition: {order.status} → {args.status}")
                results_data.append([order_id[:8] + "...",
                    "Unchanged",
                    args.status,
                    "invalid_transition"])
                continue

            # Update the status
            order.status = args.status

            # Add to batch update list
            to_update.append(order)
            results_data.append([
                order_id[:8] + "...",
                "Pending",
                f"{old_status} → {args.status}",
                order.customer_name[:15] + ("..." if len(order.customer_name) > 15 else "")
            ])

        # Save all updates in a single operation if the storage supports it
        updated_orders = []
        if to_update:
            if hasattr(self.storage, 'save_orders_batch'):
                updated_orders = self.storage.save_orders_batch(to_update)
                successful_updates = len(updated_orders)
                failed_updates = len(to_update) - successful_updates
            else:
                # Fall back to individual updates
                for order in to_update:
                    if self.storage.save_order(order):
                        successful_updates += 1
                        updated_orders.append(order)
                    else:
                        failed_updates += 1

        # Update results for reporting
        for i, result in enumerate(results_data):
            if result[1] == "Pending":
                results_data[i][1] = "Success" if i < successful_updates else "Failed"

        # Print summary
        total_processed = len(order_ids)
        print(f"\nBulk Status Update Summary:")
        print(f"  Total orders processed: {total_processed}")
        print(f"  Successfully updated:   {successful_updates}")
        print(f"  Already in target status: {unchanged}")
        print(f"  Not found:             {not_found}")
        print(f"  Failed to update:      {failed_updates}")

        # Print detailed results in verbose mode
        if args.verbose and results_data:
            print("\nDetailed Results:")
            headers = ["Order ID", "Result", "Status Change", "Customer"]
            print(tabulate(results_data, headers=headers, tablefmt="simple"))

        return updated_orders