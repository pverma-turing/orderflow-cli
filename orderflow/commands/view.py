from orderflow.commands.base import Command
from tabulate import tabulate
from datetime import datetime, date
from collections import Counter


class ViewCommand(Command):
    """Command to view all orders with filtering and statistics options"""

    VALID_STATUSES = ["new", "preparing", "delivered", "canceled"]
    DATE_FORMAT = "%Y-%m-%d"

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        # Sorting arguments
        parser.add_argument('--sort-by', choices=['order_total', 'order_time'],
                            default='order_time', help='Field to sort by')
        parser.add_argument('--reverse', action='store_true', help='Reverse the sort order')

        # Status filtering
        parser.add_argument('--status', choices=self.VALID_STATUSES,
                            help='Filter orders by status')
        parser.add_argument('--active-only', action='store_true',
                            help='Show only active orders (exclude canceled)')

        # Date filtering
        parser.add_argument('--from-date', help='Show orders from this date (YYYY-MM-DD format)')
        parser.add_argument('--to-date', help='Show orders until this date (YYYY-MM-DD format)')
        parser.add_argument('--today', action='store_true', help='Show only today\'s orders')

    def execute(self, args):
        # Get all orders
        orders = self.storage.get_orders()

        # Apply filters
        filtered_orders = self._apply_filters(orders, args)

        # Sort orders
        if args.sort_by == 'order_total':
            filtered_orders.sort(key=lambda x: x.order_total, reverse=args.reverse)
        else:  # order_time
            filtered_orders.sort(key=lambda x: x.order_time, reverse=args.reverse)

        if not filtered_orders:
            print("No orders found matching the criteria.")
            return []

        # Display orders table
        self._display_orders_table(filtered_orders)

        # Display status counts
        self._display_status_counts(orders, filtered_orders)

        # Display revenue statistics
        self._display_revenue_stats(filtered_orders)

        return filtered_orders

    def _apply_filters(self, orders, args):
        """Apply all filters to the orders list"""
        filtered_orders = []

        # Parse date filters
        from_date = None
        to_date = None

        # Handle --today shortcut
        if args.today:
            today = date.today()
            from_date = today
            to_date = today
        else:
            # Parse --from-date if provided
            if args.from_date:
                try:
                    from_date = datetime.strptime(args.from_date, self.DATE_FORMAT).date()
                except ValueError:
                    print(f"Invalid from-date format. Please use {self.DATE_FORMAT}")
                    return []

            # Parse --to-date if provided
            if args.to_date:
                try:
                    to_date = datetime.strptime(args.to_date, self.DATE_FORMAT).date()
                except ValueError:
                    print(f"Invalid to-date format. Please use {self.DATE_FORMAT}")
                    return []

        for order in orders:
            # Status filter
            if args.status and order.status != args.status:
                continue

            # Active-only filter (exclude canceled)
            if args.active_only and order.status == "canceled":
                continue

            # Date filters
            order_datetime = None
            try:
                order_datetime = datetime.fromisoformat(order.order_time)
            except (ValueError, TypeError):
                # Skip orders with invalid date format
                continue

            order_date = order_datetime.date()

            # From date filter
            if from_date and order_date < from_date:
                continue

            # To date filter
            if to_date and order_date > to_date:
                continue

            # Order passes all filters
            filtered_orders.append(order)

        return filtered_orders

    def _display_orders_table(self, orders):
        """Display orders in a formatted table"""
        table_data = []
        for order in orders:
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

    def _display_status_counts(self, all_orders, filtered_orders):
        """Display count summary of orders by status"""
        # Count orders by status from the filtered set
        status_counts = Counter(order.status for order in filtered_orders)

        # Ensure all valid statuses are represented
        for status in self.VALID_STATUSES:
            if status not in status_counts:
                status_counts[status] = 0

        # Display counts
        print("\nOrder Status Summary (filtered):")
        for status in self.VALID_STATUSES:
            print(f"  {status.capitalize()}: {status_counts[status]}")

        filtered_total = sum(status_counts.values())
        all_total = len(all_orders)

        # Display totals
        print(f"  Total (filtered): {filtered_total}")
        if filtered_total != all_total:
            print(f"  Total (all orders): {all_total}")

    def _display_revenue_stats(self, orders):
        """Display revenue statistics for the filtered orders"""
        if not orders:
            return

        # Calculate total revenue
        total_revenue = sum(order.order_total for order in orders)

        # Calculate average order value
        avg_order_value = total_revenue / len(orders)

        # Display revenue stats
        print("\nRevenue Statistics:")
        print(f"  Total Orders: {len(orders)}")
        print(f"  Total Revenue: ${total_revenue:.2f}")
        print(f"  Average Order Value: ${avg_order_value:.2f}")

        # Calculate revenue by status
        status_revenue = {}
        for status in self.VALID_STATUSES:
            status_orders = [order for order in orders if order.status == status]
            if status_orders:
                status_revenue[status] = sum(order.order_total for order in status_orders)
            else:
                status_revenue[status] = 0.0

        print("\nRevenue by Status:")
        for status in self.VALID_STATUSES:
            print(f"  {status.capitalize()}: ${status_revenue[status]:.2f}")