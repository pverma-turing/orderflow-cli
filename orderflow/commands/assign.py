from orderflow.commands.base import Command


class AssignCommand(Command):
    """Command to assign an order to a delivery partner"""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        parser.add_argument("--id", type=str, required=True,
                            help="Order ID to assign")
        parser.add_argument("--partner-name", type=str, required=True,
                            help="Name of the delivery partner")
        parser.add_argument("--eta", type=str, required=True,
                            help="Expected delivery time (e.g., 17:30)")

    def execute(self, args):
        """Execute the assign command"""

        # Try to load the order
        order = self.storage.get_order(args.id)

        # Validate that the order exists
        if not order:
            print(f"Error: Order with ID {args.id} not found.")
            return

        # Update the order with delivery partner info
        order.delivery_partner = args.partner_name
        order.eta = args.eta

        # Save the updated order
        self.storage.save_order(order)

        # Show confirmation message
        print(f"Order {args.id} assigned to {args.partner_name} (ETA: {args.eta})")