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

        # Dry-run flag
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview changes without saving')

    def _compute_updates(self, order, args):
        """
        Compute updates to be applied based on the provided arguments.
        Returns a tuple of (updated_order, changes_summary).
        """
        # Create a copy of the order to avoid modifying the original during dry-run
        updated_order = order.to_dict()  # Shallow copy is sufficient for our needs

        # Prepare a list to track changes for reporting
        changes = []

        # Update customer name if provided and valid
        if args.customer_name is not None:
            if args.customer_name.strip():  # Check if non-empty after stripping whitespace
                if args.customer_name != order.get('customer_name', ''):
                    changes.append(f"Customer name: '{order.get('customer_name', '')}' → '{args.customer_name}'")
                    updated_order['customer_name'] = args.customer_name
            else:
                self.warn("Customer name cannot be blank - skipping this update")

        # Update total if provided
        if args.total is not None:
            if args.total >= 0:  # Ensure total is non-negative
                if args.total != order.get('order_total', 0):
                    changes.append(f"Order total: {order.get('order_total', 0)} → {args.total}")
                    updated_order['order_total'] = args.total
            else:
                self.warn("Order total cannot be negative - skipping this update")

        # Handle tag updates
        tags_to_add = []
        tags_to_remove = []

        # Ensure tags field exists
        if 'tags' not in updated_order:
            updated_order['tags'] = []

        # Identify tags to add (ensuring uniqueness)
        for tag in args.add_tag:
            if tag and tag not in updated_order['tags']:
                tags_to_add.append(tag)
                updated_order['tags'].append(tag)

        # Identify tags to remove
        for tag in args.remove_tag:
            if tag and tag in updated_order['tags']:
                tags_to_remove.append(tag)
                updated_order['tags'].remove(tag)

        # Add tag changes to the summary
        if tags_to_add:
            changes.append(f"Add tags: {', '.join(tags_to_add)}")
        if tags_to_remove:
            changes.append(f"Remove tags: {', '.join(tags_to_remove)}")

        # Update note if provided
        if args.note is not None:
            if args.note != order.get('note', ''):
                changes.append("Note updated")
                updated_order['note'] = args.note

        return updated_order, changes

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
            self.error("At least one field must be provided to update")
            return 1

        # Retrieve the order to be updated
        order_id = args.id
        try:
            order = self.storage.get_order(order_id)
        except KeyError:
            self.error(f"Order with ID {order_id} not found")
            return 1

        # Compute the updates to be applied
        updated_order, changes = self._compute_updates(order, args)

        # Handle dry-run mode
        if args.dry_run:
            if changes:
                print(f"Dry run: Changes that would be applied to order {order_id}:")
                for change in changes:
                    print(f"- {change}")
            else:
                print(f"Dry run: No changes would be made to order {order_id}")
            return 0

        # Regular mode: apply and save the changes
        if changes:
            # Save the updated order
            self.storage.save_order(updated_order)

            # Print summary of updates
            print(f"Order {order_id} updated:")
            for change in changes:
                print(f"- {change}")
        else:
            print(f"No changes made to order {order_id}")

        return 0