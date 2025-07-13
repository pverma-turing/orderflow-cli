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
        # Just print the values provided by the user
        print(f"Assigning order {args.id} to {args.partner_name} with ETA: {args.eta}")