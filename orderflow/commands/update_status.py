from orderflow.commands.base import Command
from orderflow.models.order import Order


class UpdateStatusCommand(Command):
    """Command to update the status of an existing order"""

    VALID_STATUSES = Order.VALID_STATUSES

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        parser.add_argument(
            'order_id',
            help='ID of the order to update'
        )
        parser.add_argument(
            '--status',
            choices=self.VALID_STATUSES,
            required=True,
            help=f'New status for the order (choices: {", ".join(self.VALID_STATUSES)})'
        )

        # Add examples to epilog
        parser.epilog = """
Examples:
  # Update an order to "preparing" status
  orderflow update-status 12345678-abcd-1234-efgh-123456789abc --status preparing

  # Mark an order as delivered
  orderflow update-status 12345678-abcd-1234-efgh-123456789abc --status delivered

  # Cancel an order
  orderflow update-status 12345678-abcd-1234-efgh-123456789abc --status canceled
"""

    def execute(self, args):
        try:
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
            order.status = args.status

            # Save the updated order
            updated_order = self.storage.save_order(order)

            if updated_order:
                print(f"Order {order.order_id} status updated from '{old_status}' to '{args.status}'")

                # Display additional order details for confirmation
                print(f"Customer: {order.customer_name}")
                print(f"Dishes: {', '.join(order.dish_names)}")
                print(f"Total: ${order.order_total:.2f}")

                return updated_order
            else:
                print("Failed to update order status. Please check the errors above.")
                return None

        except ValueError as e:
            print(f"Error: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return None