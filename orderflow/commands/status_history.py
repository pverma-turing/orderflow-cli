import datetime

from orderflow.commands.base import Command


class StatusHistoryCommand(Command):
    def add_arguments(self, parser):
        parser.add_argument("--id", required=True, help="ID of the order to show status history")
        parser.add_argument("--audit", action="store_true",
                            help="Display history in plain-text audit log format")
        parser.add_argument("--since",
                            help="Show only status changes since this timestamp (ISO format: YYYY-MM-DDThh:mm)")

    def __init__(self, storage):
        self.storage = storage

    def execute(self, args):
        # Validate the --since timestamp if provided
        since_timestamp = None
        if args.since:
            try:
                since_timestamp = datetime.datetime.fromisoformat(args.since)
            except ValueError:
                print(f"[Error] Invalid timestamp format '{args.since}'. Please use ISO format (YYYY-MM-DDThh:mm).")
                return

        # Get the order and handle not found error
        order = self.storage.get_order(args.id)
        if not order:
            print(f"[Error] Order ID {args.id} not found.")
            return

        # Display order metadata header - common to all display modes
        self._display_order_metadata(order, args.id)

        # Handle orders without status_history (backward compatibility)
        if not hasattr(order, 'status_history') or not order.status_history:
            print(f"[Error] No status history available for Order ID {args.id}.")
            return

        # Filter history entries if --since is provided
        filtered_history = order.status_history
        if since_timestamp:
            filtered_history = []
            for entry in order.status_history:
                entry_timestamp = entry[0]
                entry_dt = datetime.datetime.fromisoformat(entry_timestamp)
                if entry_dt >= since_timestamp:
                    filtered_history.append(entry)

        # Check if we have any matching entries after filtering
        if not filtered_history:
            print(f"No status changes since {args.since}.")
            return

        # Handle audit log format
        if args.audit:
            self._display_audit_log(filtered_history)
        else:
            self._display_table_format(filtered_history, order.order_time)

    def _display_order_metadata(self, order, order_id):
        """Display order metadata header with creation information."""
        # Format creation timestamp for readability
        created_at = datetime.datetime.fromisoformat(order.order_time).strftime("%Y-%m-%d %H:%M:%S")

        # Create a consistent header box
        print("┌" + "─" * 50 + "┐")
        print(f"│ Order Information                                  │")
        print("├" + "─" * 50 + "┤")
        print(f"│ Order ID:       {order_id:<34} │")
        print(f"│ Customer:       {order.customer_name:<34} │")
        print(f"│ Created At:     {created_at:<34} │")
        print(f"│ Current Status: {order.status:<34} │")

        # Add order total if available
        if hasattr(order, 'order_total'):
            print(f"│ Order Total:    {order.order_total:<34} │")

        # Add dish count if available
        if hasattr(order, 'dishes') and order.dishes:
            dish_count = len(order.dishes) if isinstance(order.dishes, list) else 1
            print(f"│ Dishes:         {dish_count:<34} │")

        # Add tags if available and not empty
        if hasattr(order, 'tags') and order.tags:
            tags_str = ", ".join(order.tags) if len(", ".join(order.tags)) <= 34 else f"{len(order.tags)} tags"
            print(f"│ Tags:           {tags_str:<34} │")

        print("└" + "─" * 50 + "┘")
        print()  # Add a blank line for separation

    def _display_audit_log(self, history_entries):
        """Display status history in plain-text audit log format."""
        print("--- STATUS AUDIT LOG ---")

        # Print each status change in chronological order
        for entry in history_entries:
            # Handle different entry formats (backward compatibility)
            if len(entry) == 2:  # Old format: (timestamp, status)
                timestamp, status, note = entry[0], entry[1], None
            else:  # New format: (timestamp, status, note)
                timestamp, status, note = entry

            # Format the log entry
            log_entry = f"[{timestamp}] Status changed to: {status}"
            if note:
                log_entry += f" [Note: {note}]"

            print(log_entry)

        # Print a separator to mark the end of the log
        print("--- END OF AUDIT LOG ---")

    def _display_table_format(self, history_entries, order_time):
        """Display status history in tabular format."""
        print("Status History:")

        # Determine table width based on content
        has_notes = any(len(entry) > 2 and entry[2] for entry in history_entries)
        if has_notes:
            print("-" * 90)
            print(f"{'Timestamp':<25} {'Status':<15} {'Duration':<15} {'Note'}")
            print("-" * 90)
        else:
            print("-" * 60)
            print(f"{'Timestamp':<25} {'Status':<15} {'Duration':<15}")
            print("-" * 60)

        # Loop through history entries
        prev_time = None
        for i, entry in enumerate(history_entries):
            # Handle different entry formats (backward compatibility)
            if len(entry) == 2:  # Old format: (timestamp, status)
                timestamp, status, note = entry[0], entry[1], None
            else:  # New format: (timestamp, status, note)
                timestamp, status, note = entry

            # Format the timestamp for display
            dt = datetime.datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")

            # Calculate duration (only if not the first entry after filtering)
            duration = ""
            if i > 0 and prev_time:
                prev_dt = datetime.datetime.fromisoformat(prev_time)
                delta = dt - prev_dt
                duration = str(delta).split('.')[0]  # Remove microseconds

            # Print row with or without note
            if has_notes:
                note_text = note if note else ""
                print(f"{formatted_time:<25} {status:<15} {duration:<15} {note_text}")
            else:
                print(f"{formatted_time:<25} {status:<15} {duration:<15}")

            prev_time = timestamp

        # Print footer line with appropriate width
        if has_notes:
            print("-" * 90)
        else:
            print("-" * 60)

        # Calculate and display filtered duration if appropriate
        if len(history_entries) > 1:
            first_timestamp = history_entries[0][0]
            last_timestamp = history_entries[-1][0]
            first_dt = datetime.datetime.fromisoformat(first_timestamp)
            last_dt = datetime.datetime.fromisoformat(last_timestamp)
            filtered_duration = last_dt - first_dt
            print(f"Duration in filtered view: {str(filtered_duration).split('.')[0]}")