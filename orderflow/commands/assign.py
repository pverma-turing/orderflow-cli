import datetime
import json
import re
import iso8601
from orderflow.commands.base import Command
from orderflow.models.delivery_info import DeliveryInfo


class AssignCommand(Command):
    """Command to assign an order to a delivery partner"""

    def __init__(self, storage):
        self.storage = storage

    # Mock delivery partner registry
    VALID_PARTNERS = ["Ravi", "Meena", "Ali", "Kavita"]

    # ETA format regex pattern for relative time (e.g., 30m, 2h, 1h30m)
    ETA_RELATIVE_PATTERN = re.compile(r'^((\d+)h)?((\d+)m)?$')

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
                            help="Expected delivery time (e.g., '30m', '2h', '1h30m', or ISO format)")

        # Add reassign flag
        parser.add_argument("--reassign", action="store_true",
                            help="Reassign an already assigned order to a different delivery partner")

        # Add dry-run flag
        parser.add_argument("--dry-run", action="store_true",
                            help="Simulate the operation without making actual changes")

    def _validate_eta_format(self, eta_str):
        """
        Validate ETA format. Accepts:
        - Relative time (e.g., 30m, 2h, 1h30m)
        - ISO format (e.g., 2025-07-10T15:30:00)

        Returns:
            bool: True if format is valid, False otherwise
        """
        # Check for relative time format
        relative_match = self.ETA_RELATIVE_PATTERN.match(eta_str)
        if relative_match and (relative_match.group(2) or relative_match.group(4)):
            return True

        # Check for ISO format
        try:
            iso8601.parse_date(eta_str)
            return True
        except (ValueError, iso8601.ParseError):
            return False

    def _record_history_entry(self, order, action, partner_name=None, eta=None, dry_run=False):
        """Record an entry in the order's assignment history"""
        timestamp = datetime.datetime.now().isoformat()

        history_entry = {
            "action": action,
            "timestamp": timestamp
        }

        # Add partner and ETA info based on action type
        if action == "assign" or action == "reassign":
            history_entry["partner_name"] = partner_name
            history_entry["eta"] = eta
        elif action == "unassign" and partner_name:
            history_entry["removed_partner"] = partner_name

        if dry_run:
            print(f"DRY RUN: Would record in history: {json.dumps(history_entry)}")
            return

        # Initialize assignment_history if it doesn't exist
        if not hasattr(order, 'assignment_history') or order.assignment_history is None:
            order.assignment_history = []

        # Add the history entry
        order.assignment_history.append(history_entry)

        print("Assignment recorded in order history.")

    def execute(self, args):
        """Execute the assign command"""
        # Get the storage instance
        storage = self.storage

        # Log dry run status if enabled
        if args.dry_run:
            print("DRY RUN: Simulating operation without making changes.")

        # Try to load the order
        order = storage.get_order(args.id)

        # Validate that the order exists
        if not order:
            print(f"Error: Order with ID {args.id} not found.")
            return

        if args.dry_run:
            print(f"DRY RUN: Found order with ID {args.id}")

        # Unassignment logic
        if args.unassign:
            if not order.delivery_info:
                print(f"Order {args.id} is not currently assigned.")
                return

            # Get the current partner name before unassigning
            removed_partner = order.delivery_info.partner_name

            if args.dry_run:
                print(f"DRY RUN: Would unassign order {args.id} from {removed_partner}")
                self._record_history_entry(order, "unassign", partner_name=removed_partner, dry_run=True)
            else:
                # Clear the delivery info
                order.delivery_info = None

                # Record unassignment in history
                self._record_history_entry(order, "unassign", partner_name=removed_partner)

                # Save the updated order
                storage.save_order(order)

            # Show confirmation message
            if args.dry_run:
                print(f"DRY RUN: Would print: Order {args.id} has been unassigned.")
            else:
                print(f"Order {args.id} has been unassigned.")

            if args.dry_run:
                print("Dry run complete. No changes were made.")
            return

        # Assignment validation

        # 1. Validate that eta is provided when partner_name is given
        if not args.eta:
            print("Error: --eta is required when assigning an order.")
            return

        if args.dry_run:
            print(f"DRY RUN: ETA parameter provided: {args.eta}")

        # 2. Validate the ETA format
        if not self._validate_eta_format(args.eta):
            print(
                f"Error: Invalid ETA format '{args.eta}'. Use either a relative time (e.g., '30m', '2h', '1h30m') or ISO format (e.g., '2025-07-10T15:30:00').")
            return

        if args.dry_run:
            print(f"DRY RUN: ETA format validation passed for '{args.eta}'")

        # 3. Validate the partner name
        if args.partner_name not in self.VALID_PARTNERS:
            print(f"Error: Delivery partner '{args.partner_name}' is not registered.")
            return

        if args.dry_run:
            print(f"DRY RUN: Partner '{args.partner_name}' validation passed")

        # 4. Check if the order is already assigned
        previous_partner = None
        previous_eta = None
        is_reassign = False

        if order.delivery_info:
            # If already assigned and --reassign flag is not provided, show error
            if not args.reassign:
                print(
                    f"Order {args.id} is already assigned to {order.delivery_info.partner_name} with ETA {order.delivery_info.eta}. Use --reassign to override.")
                return

            # Store the previous assignment info for the summary message
            previous_partner = order.delivery_info.partner_name
            previous_eta = order.delivery_info.eta
            is_reassign = True

            if args.dry_run:
                print(f"DRY RUN: Order is already assigned to {previous_partner} with ETA {previous_eta}")
                print(f"DRY RUN: Reassignment mode is active")

        # All validations passed, proceed with assignment
        action_type = "reassign" if is_reassign else "assign"

        if args.dry_run:
            print(f"DRY RUN: Would create DeliveryInfo with partner_name={args.partner_name}, eta={args.eta}")
            self._record_history_entry(order, action_type, args.partner_name, args.eta, dry_run=True)

            # Show what message would be shown
            if is_reassign:
                print(
                    f"DRY RUN: Would print: Order {args.id} reassigned from {previous_partner} (ETA: {previous_eta}) to {args.partner_name} (ETA: {args.eta})")
            else:
                print(f"DRY RUN: Would print: Order {args.id} assigned to {args.partner_name} (ETA: {args.eta})")

            print("Dry run complete. No changes were made.")
            return

        # Create DeliveryInfo object (only if not dry run)
        delivery_info = DeliveryInfo(
            partner_name=args.partner_name,
            eta=args.eta
        )

        # Update the order with delivery partner info
        order.delivery_info = delivery_info

        # Record assignment or reassignment in history
        self._record_history_entry(order, action_type, args.partner_name, args.eta)

        # Save the updated order
        storage.save_order(order)

        # Show confirmation message
        if is_reassign:
            print(
                f"Order {args.id} reassigned from {previous_partner} (ETA: {previous_eta}) to {args.partner_name} (ETA: {args.eta})")
        else:
            print(f"Order {args.id} assigned to {args.partner_name} (ETA: {args.eta})")