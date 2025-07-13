from orderflow.commands.base import Command
from orderflow.models.delivery_info import DeliveryInfo


class AssignCommand(Command):
    """Command to assign an order to a delivery partner"""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        parser.add_argument("--id", type=str, required=True,
                            help="Order ID to assign or unassign")

        # Create mutually exclusive group for assignment vs. unassignment
        group = parser.add_mutually_exclusive_group(required=True)

        # Assignment options
        group.add_argument("--partner-name", type=str,
                           help="Name of the delivery partner")

        # Unassignment option
        group.add_argument("--unassign", action="store_true",
                           help="Unassign a previously assigned order")

        # Make ETA required only when --partner-name is specified
        parser.add_argument("--eta", type=str,
                            help="Expected delivery time (e.g., 17:30)")

    def execute(self, args):
        """Execute the assign command"""
        # Validate that eta is provided when partner_name is given
        if args.partner_name and not args.eta:
            print("Error: --eta is required when assigning an order.")
            return

        # Get the storage instance
        storage = self.storage

        # Try to load the order
        order = storage.get_order(args.id)

        # Validate that the order exists
        if not order:
            print(f"Error: Order with ID {args.id} not found.")
            return

        # Unassignment logic
        if args.unassign:
            if not order.delivery_info:
                print(f"Order {args.id} is not currently assigned.")
                return

            # Clear the delivery info
            order.delivery_info = None

            # Save the updated order
            storage.save_order(order)

            # Show confirmation message
            print(f"Order {args.id} has been unassigned.")
            return

        # Assignment logic (only reached if --unassign is not used)
        # Check if the order is already assigned
        if order.delivery_info:
            print(f"Order {args.id} is already assigned to {order.delivery_info.partner_name} "
                  f"with ETA {order.delivery_info.eta}")
            return

        # Create and assign DeliveryInfo
        delivery_info = DeliveryInfo(
            partner_name=args.partner_name,
            eta=args.eta
        )

        # Update the order with delivery partner info
        order.delivery_info = delivery_info

        # Save the updated order
        storage.save_order(order)

        # Show confirmation message
        print(f"Order {args.id} assigned to {args.partner_name} (ETA: {args.eta})")