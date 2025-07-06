from orderflow.commands.base import Command


class UpdateStatusCommand(Command):
    """Command to update the status of an existing order"""

    VALID_STATUSES = ["new", "preparing", "delivered", "canceled"]

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        parser.add_argument('order_id', help='ID of the order to update')
        parser.add_argument('--status',
                            choices=self.VALID_STATUSES,
                            required=True,
                            help='New status for the order')

    def execute(self, args):
        # Get the order
        order = self.storage.get_order(args.order_id)

        if not order:
            print(f"Error: Order with ID {args.order_id} not found.")
            return None

        # Update the status
        old_status = order.status
        order.status = args.status

        # Save the updated order
        self.storage.save_order(order)

        print(f"Order {order.order_id} status updated from '{old_status}' to '{args.status}'")
        return order