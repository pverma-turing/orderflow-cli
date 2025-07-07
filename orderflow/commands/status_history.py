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
                print(f"Error: Invalid timestamp format '{args.since}'. Please use ISO format (YYYY-MM-DDThh:mm)")
                return

        order = self.storage.get_order(args.id)

        if not order:
            print(f"Order {args.id} not found")
            return

        # Handle orders without status_history (backward compatibility)
        if not hasattr(order, 'status_history'):
            if since_timestamp:
                order_time_dt = datetime.datetime.fromisoformat(order.order_time)
                if order_time_dt < since_timestamp:
                    print(f"No status changes since {args.since}")
                    return

            if args.audit:
                print(f"ORDER: {args.id} | CUSTOMER: {order.customer_name}")
                print(f"[{order.order_time}] Status set to: {order.status}")
                return
            else:
                print(f"Order {args.id} - {order.customer_name}")
                print("No status history recorded. Only current status is available.")
                print(f"Current status: {order.status} (since order creation)")
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
            print(f"No status changes since {args.since}")
            return

        # Handle audit log format
        if args.audit:
            self._display_audit_log(order, args.id, filtered_history)
        else:
            self._display_table_format(order, filtered_history)

    def _display_audit_log(self, order, order_id, history_entries):
        """Display status history in plain-text audit log format."""
        # Print order header info
        print(f"ORDER: {order_id} | CUSTOMER: {order.customer_name}")
        print(f"CREATED: {order.order_time}")
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

    def _display_table_format(self, order, history_entries):
        """Display status history in tabular format."""
        # Display order information and status history header
        print(f"Order {order.order_id} - {order.customer_name}")
        print(f"Created: {order.order_time}")
        print("\nStatus History:")

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

        # Display current status
        print(f"Current status: {order.status}")