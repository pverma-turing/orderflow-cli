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
    """Command to add a new order with dish quantities"""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        # Required arguments
        parser.add_argument(
            '--customer-name',
            required=True,
            help='Name of the customer (required)'
        )

        # Handle both old and new dish parameter formats
        dish_group = parser.add_mutually_exclusive_group(required=True)
        dish_group.add_argument(
            '--dishes',
            help='Comma-separated list of dishes with optional quantities (e.g., "Paneer Tikka:2, Garlic Naan:3")'
        )
        # Backward compatibility
        dish_group.add_argument(
            '--dish-names',
            help='DEPRECATED: Use --dishes instead. Comma-separated list of dish names.'
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
  # Add order with dish quantities
  orderflow add --customer-name "John Doe" --dishes "Burger:1,Fries:2,Soda:1" --order-total 15.99

  # Add order with regular dishes (quantity defaults to 1)
  orderflow add --customer-name "Jane Smith" --dishes "Pizza, Salad" --order-total 24.99

  # Add order with additional details
  orderflow add --customer-name "Bob Johnson" --dishes "Pasta:1,Garlic Bread:2" --order-total 12.50 --status preparing --tags "dine-in,special" --notes "Allergic to nuts"
"""

    def execute(self, args):
        try:
            # Determine which dish argument was used
            dishes = args.dishes if args.dishes else args.dish_names

            # Create a new order (validation happens in the Order constructor)
            order = Order(
                customer_name=args.customer_name,
                dishes=dishes,
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
                print(f"Dishes: {order.get_formatted_dishes()}")
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