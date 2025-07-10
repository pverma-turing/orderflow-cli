from datetime import datetime

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
        parser.add_argument('--order-time', help='Update order time (ISO 8601 format, e.g., 2024-07-10T15:30:00)')

        # Dry-run flag
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview changes without saving')

    def _parse_iso_datetime(self, datetime_str):
        """
        Parse an ISO 8601 datetime string.
        Returns a datetime object if valid, None otherwise.
        """
        try:
            return datetime.fromisoformat(datetime_str)
        except ValueError:
            self.error(
                f"Invalid datetime format: '{datetime_str}'. Expected ISO 8601 format (e.g., 2024-07-10T15:30:00)")
            return None

    def _get_order_and_validate(self, order_id):
        """
        Retrieve the order and validate it exists.
        Returns the order if found, None otherwise.
        """
        try:
            order = self.storage.get_order(order_id)
            return order
        except KeyError:
            self.error(f"Order with ID {order_id} not found")
            return None

    def _compute_field_differences(self, order, args):
        """
        Compute field differences based on the provided arguments.
        Returns a list of human-readable change descriptions.
        """
        changes = []

        # Check customer name change
        if args.customer_name is not None:
            if args.customer_name.strip():  # Non-empty after stripping
                if args.customer_name != order.customer_name:
                    changes.append(f"Customer name: '{order.customer_name}' → '{args.customer_name}'")
            else:
                self.warn("Customer name cannot be blank - skipping this update")

        # Check total change
        if args.total is not None:
            if args.total >= 0:  # Ensure total is non-negative
                if args.total != order.order_total:
                    changes.append(f"Order total: {order.order_total} → {args.total}")
            else:
                self.warn("Order total cannot be negative - skipping this update")

        # Calculate tag changes
        tags_to_add = []
        for tag in args.add_tag:
            if tag and tag not in order.tags:
                tags_to_add.append(tag)

        tags_to_remove = []
        for tag in args.remove_tag:
            if tag and tag in order.tags:
                tags_to_remove.append(tag)

        # Add tag changes to summary
        if tags_to_add:
            changes.append(f"Add tags: {', '.join(tags_to_add)}")
        if tags_to_remove:
            changes.append(f"Remove tags: {', '.join(tags_to_remove)}")

        # Check note change
        if args.note is not None:
            if getattr(order, 'note', '') != args.note:
                changes.append("Note updated")

        # Check order time change
        if args.order_time is not None:
            new_time = self._parse_iso_datetime(args.order_time)
            if new_time is not None:
                current_time = getattr(order, 'order_time', None)
                if current_time != new_time:
                    # Format for display
                    current_display = current_time.isoformat() if current_time else "None"
                    changes.append(f"Order time: {current_display} → {new_time.isoformat()}")

        return changes

    def _apply_updates(self, order, args):
        """
        Apply all updates to the order object.
        """
        # Update customer name if valid
        if args.customer_name is not None and args.customer_name.strip():
            order.customer_name = args.customer_name

        # Update total if valid
        if args.total is not None and args.total >= 0:
            order.order_total = args.total

        # Ensure tags attribute exists
        if not hasattr(order, 'tags'):
            order.tags = []

        # Add new tags (ensuring uniqueness)
        for tag in args.add_tag:
            if tag and tag not in order.tags:
                order.tags.append(tag)

        # Remove specified tags
        for tag in args.remove_tag:
            if tag and tag in order.tags:
                order.tags.remove(tag)

        # Update note if provided
        if args.note is not None:
            order.note = args.note

        # Update order time if provided and valid
        if args.order_time is not None:
            new_time = self._parse_iso_datetime(args.order_time)
            if new_time is not None:
                order.order_time = new_time

    def _print_update_summary(self, changes, dry_run=False):
        """
        Print a summary of the updates applied or to be applied.
        """
        if not changes:
            if dry_run:
                print("Dry run: No changes would be made")
            else:
                print("No changes were made")
            return

        if dry_run:
            print("Dry run: Changes that would be applied:")
        else:
            print("Applied changes:")

        for change in changes:
            print(f"- {change}")

    def execute(self, args):
        """Execute the update command."""
        # Validate that at least one update field was provided
        update_fields = [
            args.customer_name is not None,
            args.total is not None,
            len(args.add_tag) > 0,
            len(args.remove_tag) > 0,
            args.note is not None,
            args.order_time is not None
        ]

        if not any(update_fields):
            self.error("At least one field must be provided to update")
            return 1

        # If order time is provided, validate it early
        if args.order_time is not None and self._parse_iso_datetime(args.order_time) is None:
            return 1  # Error already printed by _parse_iso_datetime

        # Retrieve and validate the order
        order = self._get_order_and_validate(args.id)
        if order is None:
            return 1

        # Compute field differences
        changes = self._compute_field_differences(order, args)

        # Handle dry-run mode
        if args.dry_run:
            self._print_update_summary(changes, dry_run=True)
            return 0

        # Apply updates to the order
        self._apply_updates(order, args)

        # Save the updated order
        if changes:
            self.storage.save_order(order)

        # Print summary
        self._print_update_summary(changes)

        return 0