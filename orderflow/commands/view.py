from orderflow.commands.base import Command
from tabulate import tabulate
from datetime import datetime


class ViewCommand(Command):
    """Command to view all orders"""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        parser.add_argument('--sort-by', choices=['order_total', 'order_time'],
                            default='order_time', help='Field to sort by')
        parser.add_argument('--reverse', action='store_true', help='Reverse the sort order')

    def execute(self, args):
        # Get all orders
        orders = self.storage.get_orders()

        # Sort orders
        if args.sort_by == 'order_total':
            orders.sort(key=lambda x: x.order_total, reverse=args.reverse)
        else:  # order_time
            orders.sort(key=lambda x: x.order_time, reverse=args.reverse)

        if not orders:
            print("No orders found.")
            return []

        # Format data for display
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
                ", ".join(order.dish_names),
                f"${order.order_total:.2f}",
                order.status,
                formatted_time
            ])

        # Display table
        headers = ["Order ID", "Customer", "Dishes", "Total", "Status", "Time"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        return orders