import argparse
from orderflow.commands.base import Command
from orderflow.models.order import Order


class PositiveFloat(argparse.Action):
    """Custom argparse action to validate positive float values"""

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            value = float(values)
            if value <= 0:
                parser.error(f"{option_string} must be a positive number")
            setattr(namespace, self.dest, value)
        except ValueError:
            parser.error(f"{option_string} must be a valid number")


class AddCommand(Command):
    """Command to add a new order with input validation"""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        # Required arguments
        parser.add_argument(
            '--customer-name',
            required=True,
            help='Name of the customer (required)'
        )
        parser.add_argument(
            '--dish-names',
            required=True,
            help='Comma-separated list of dish names (required, e.g., "Pizza,Salad,Soda")'
        )
        parser.add_argument(
            '--order-total',
            required=True,
            action=PositiveFloat,
            help='Total amount of the order (required, must be a positive number)'
        )

        # Optional arguments
        parser.add_argument(
            '--status',
            choices=Order.VALID_STATUSES,
            default='new',
            help=f'Order status (default: "new", choices: {", ".join(Order.VALID_STATUSES)})'
        )
        parser.add_argument(
            '--tags',
            help='Comma-separated list of tags (e.g., "takeaway,zomato,spicy")'
        )
        parser.add_argument(
            '--notes',
            help='Additional notes about the order'
        )

        # Add examples to epilog
        parser.epilog = """
Examples:
  orderflow add --customer-name "John Doe" --dish-names "Burger,Fries" --order-total 15.99
  orderflow add --customer-name "Jane Smith" --dish-names "Pizza,Salad" --order-total 24.99 --status "preparing" --tags "delivery,special"
  orderflow add --customer-name "Bob Johnson" --dish-names "Pasta" --order-total 12.50 --notes "Allergic to nuts"
"""

    def execute(self, args):
        try:
            # Create a new order (validation happens in the Order constructor)
            order = Order(
                customer_name=args.customer_name,
                dish_names=args.dish_names,
                order_total=args.order_total,
                status=args.status,
                tags=args.tags,
                notes=args.notes
            )

            # Save to storage
            saved_order = self.storage.save_order(order)

            if saved_order:
                print(f"Order added successfully with ID: {order.order_id}")

                # Display order details
                print(f"Customer: {order.customer_name}")
                print(f"Dishes: {', '.join(order.dish_names)}")
                print(f"Total: ${order.order_total:.2f}")
                print(f"Status: {order.status}")

                if order.tags:
                    print(f"Tags: {', '.join(order.tags)}")
                if order.notes:
                    print(f"Notes: {order.notes}")

                return order
            else:
                print("Failed to add order. Please check the errors above and try again.")
                return None

        except ValueError as e:
            print(f"Error: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return None