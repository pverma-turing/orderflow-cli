import datetime

from orderflow.commands.base import Command


class StatusHistoryCommand(Command):
    def add_arguments(self, parser):
        parser.add_argument("--id", required=True, help="ID of the order to show status history")

    def __init__(self, storage):
        self.storage = storage

    def execute(self, args):
        order = self.storage.get_order(args.id)

        if not order:
            print(f"Order {args.id} not found")
            return

        # Handle orders without status_history (backward compatibility)
        if not hasattr(order, 'status_history'):
            print(f"Order {args.id} - {order.customer_name}")
            print("No status history recorded. Only current status is available.")
            print(f"Current status: {order.status} (since order creation)")
            return

        # Display order information and status history header
        print(f"Order {args.id} - {order.customer_name}")
        print(f"Created: {order.order_time}")
        print("\nStatus History:")

        # Determine table width based on content
        has_notes = any(len(entry) > 2 and entry[2] for entry in order.status_history)
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
        for i, entry in enumerate(order.status_history):
            # Handle different entry formats (backward compatibility)
            if len(entry) == 2:  # Old format: (timestamp, status)
                timestamp, status, note = entry[0], entry[1], None
            else:  # New format: (timestamp, status, note)
                timestamp, status, note = entry

            # Format the timestamp for display
            dt = datetime.datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")

            # Calculate duration
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

        # Calculate and display total time since order creation
        if len(order.status_history) > 0:
            first_timestamp = order.status_history[0][0]
            first_dt = datetime.datetime.fromisoformat(first_timestamp)
            current_dt = datetime.datetime.now()
            total_time = current_dt - first_dt
            print(f"Total time since order creation: {str(total_time).split('.')[0]}")

        # Display current status
        print(f"Current status: {order.status}")