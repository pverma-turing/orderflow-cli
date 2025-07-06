from orderflow.commands.base import Command
from tabulate import tabulate
from datetime import datetime
from collections import Counter


class ViewCommand(Command):
    """Command to view all orders with filtering options"""

    VALID_STATUSES = ["new", "preparing", "delivered", "canceled"]

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        parser.add_argument('--sort-by', choices=['order_total', 'order_time'],
                            default='order_time', help='Field to sort by')
        parser.add_argument('--reverse', action='store_true', help='Reverse the sort order')
        parser.add_argument('--status', choices=self.VALID_STATUSES,
                            help='Filter orders by status')
        parser.add_argument('--active-only', action='store_true',
                            help='Show only active orders (exclude canceled)')

    def execute(self, args):
        # Get all orders
        orders = self.storage.get_orders()

        # Apply filters
        filtered_orders = []
        for order in orders:
            # Status filter
            if args.status and order.status != args.status:
                continue

            # Active-only filter (exclude canceled)
            if args.active_only and order.status == "canceled":
                continue

            filtered_orders.append(order)

        # Sort orders
        if args.sort_by == 'order_total':
            filtered_orders.sort(key=lambda x: x.order_total, reverse=args.reverse)
        else:  # order_time
            filtered_orders.sort(key=lambda x: x.order_time, reverse=args.reverse)

        if not filtered_orders:
            print("No orders found matching the criteria.")
            return []

        # Format data for display
        table_data = []
        for order in filtered_orders:
            # Format the date for better readability
            try:
                dt = datetime.fromisoformat(order.order_time)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                formatted_time = order.order_time

            table_data.append([
                order.order_id[:8] + "...",  # Truncate UUID for display
                order.customer_name,
                ", ".join(order.dish_names) if isinstance(order.dish_names, list) else order.dish_names,
                f"${order.order_total:.2f}",
                order.status,
                formatted_time
            ])

        # Display table
        headers = ["Order ID", "Customer", "Dishes", "Total", "Status", "Time"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Calculate and display status counts
        self._display_status_counts(orders)

        return filtered_orders

    def _display_status_counts(self, orders):
        """Display count summary of orders by status"""
        # Count orders by status
        status_counts = Counter(order.status for order in orders)

        # Ensure all valid statuses are represented
        for status in self.VALID_STATUSES:
            if status not in status_counts:
                status_counts[status] = 0

        # Display counts
        print("\nOrder Status Summary:")
        for status in self.VALID_STATUSES:
            print(f"  {status.capitalize()}: {status_counts[status]}")

        # Display total
        print(f"  Total: {len(orders)}")