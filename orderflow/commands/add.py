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

    def execute(self, args):
        # Create a new order
        order = Order(
            customer_name=args.customer_name,
            dish_names=args.dish_names,
            order_total=args.order_total,
            status=args.status
        )

        # Save to storage
        self.storage.save_order(order)

        print(f"Order added successfully with ID: {order.order_id}")
        return order