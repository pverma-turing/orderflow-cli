from orderflow.commands.base import Command


class UpdateCommand(Command):
    """Command for updating non-status fields of existing orders."""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        """Add update command arguments to the parser."""
        # Required argument
        parser.add_argument('--id', required=True, help='ID of the order to update')

        # Optional fields that can be updated
        parser.add_argument('--customer-name', help='New customer name')
        parser.add_argument('--total', type=float, help='Updated order total')
        parser.add_argument('--add-tag', action='append', default=[],
                            help='Tag to add (can specify multiple times)')
        parser.add_argument('--remove-tag', action='append', default=[],
                            help='Tag to remove (can specify multiple times)')
        parser.add_argument('--note', help='Replace the order-level note')

    def execute(self, args):
        """Execute the update command."""
        # Validate that at least one update field was provided
        update_fields = [
            args.customer_name is not None,
            args.total is not None,
            len(args.add_tag) > 0,
            len(args.remove_tag) > 0,
            args.note is not None
        ]

        if not any(update_fields):
            print("At least one field must be provided to update")
            return 1

        # Just print a confirmation message for now
        print(f"Ready to update order {args.id}")

        return 0