from orderflow.commands.base import Command
from orderflow.models.order import Order


class AddCommand(Command):
    """Command to add a new order"""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        parser.add_argument('--customer-name', required=True, help='Name of the customer')
        parser.add_argument('--dish-names', required=True, help='Comma-separated list of dish names')
        parser.add_argument('--order-total', required=True, type=float, help='Total amount of the order')
        parser.add_argument('--status', default='new', help='Order status (default: new)')
        # New arguments
        parser.add_argument('--tags', help='Comma-separated list of tags (e.g. "takeaway, zomato")')
        parser.add_argument('--notes', help='Additional notes about the order')

    def execute(self, args):
        # Create a new order
        order = Order(
            customer_name=args.customer_name,
            dish_names=args.dish_names,
            order_total=args.order_total,
            status=args.status,
            tags=args.tags,
            notes=args.notes
        )

        # Save to storage
        self.storage.save_order(order)

        print(f"Order added successfully with ID: {order.order_id}")

        # Display order details
        if order.tags:
            print(f"Tags: {', '.join(order.tags)}")
        if order.notes:
            print(f"Notes: {order.notes}")

        return order