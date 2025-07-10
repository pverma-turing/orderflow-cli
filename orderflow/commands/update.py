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

        # Retrieve the order to be updated
        order_id = args.id
        try:
            order = self.storage.get_order(order_id)
        except KeyError:
            print(f"Order with ID {order_id} not found")
            return 1

        # Track what was updated for the summary
        updates = []

        # Update customer name if provided and valid
        if args.customer_name is not None:
            if args.customer_name.strip():  # Check if non-empty after stripping whitespace
                order.customer_name = args.customer_name
                updates.append("customer name")
            else:
                print("Customer name cannot be blank - skipping this update")

        # Update total if provided
        if args.total is not None:
            if args.total >= 0:  # Ensure total is non-negative
                order.order_total = args.total
                updates.append("order total")
            else:
                print("Order total cannot be negative - skipping this update")

        # Handle tag updates
        added_tags = 0
        removed_tags = 0

        # Ensure tags field exists
        if not hasattr(order, 'tags'):
            order.tags = []

        # Add tags (ensuring uniqueness)
        for tag in args.add_tag:
            if tag and tag not in order.tags:
                order.tags.append(tag)
                added_tags += 1

        # Remove tags (idempotent operation)
        for tag in args.remove_tag:
            if tag and tag in order['tags']:
                order.tags.remove(tag)
                removed_tags += 1

        # Update tag summary if changes were made
        if added_tags > 0:
            updates.append(f"added {added_tags} tag{'s' if added_tags > 1 else ''}")
        if removed_tags > 0:
            updates.append(f"removed {removed_tags} tag{'s' if removed_tags > 1 else ''}")

        # Update note if provided
        if args.note is not None:
            order.notes = args.note
            updates.append("order note")

        # Save the updated order
        self.storage.save_order(order)

        # Print summary of updates
        if updates:
            update_str = ", ".join(updates)
            print(f"Order {order_id} updated: {update_str}")
        else:
            print(f"No changes made to order {order_id}")

        return 0