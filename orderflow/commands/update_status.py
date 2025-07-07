import datetime

from orderflow.commands.base import Command


class UpdateStatusCommand(Command):
    # Status transition rules dictionary
    VALID_TRANSITIONS = {
        "new": ["preparing", "canceled"],
        "preparing": ["delivered", "canceled"],
        "delivered": [],  # No further transitions allowed
        "canceled": []  # No further transitions allowed
    }

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        # Create mutually exclusive group for status change vs rollback
        action_group = parser.add_mutually_exclusive_group(required=True)
        action_group.add_argument("--status", choices=["preparing", "delivered", "canceled"],
                                  help="New status to set for the order(s)")
        action_group.add_argument("--rollback", action="store_true",
                                  help="Roll back to the previous status (cannot be used with --ids)")

        parser.add_argument("--id", help="ID of order to update")
        parser.add_argument("--ids", nargs="+", help="IDs of orders to update (not valid with --rollback)")
        parser.add_argument("--note", help="Optional note to associate with this status change")
        parser.add_argument("--show-history", action="store_true",
                            help="Show the status history before applying changes (only works with --id)")

    def execute(self, args):
        # Check for invalid show-history combinations
        if args.show_history and args.ids:
            print("Warning: --show-history is ignored when using --ids for batch updates")
        elif args.show_history and args.rollback:
            print("Warning: --show-history is ignored when using --rollback")

        # Validate arguments
        if args.rollback:
            if args.ids:
                print("Error: Bulk rollback with --ids is not supported. Please use --id for a single order.")
                return
            if args.note:
                print("Error: Cannot use --note with --rollback.")
                return
            if not args.id:
                print("Error: Order ID is required for rollback. Please use --id.")
                return

            # Process rollback for single order
            self._process_rollback(args.id, self.storage)
        else:
            # Process normal status update (existing functionality)
            # Get current timestamp for this update
            timestamp = datetime.datetime.now().isoformat()

            if args.ids:
                self._process_batch_update(args.ids, args.status, args.note, timestamp, self.storage)
            elif args.id:
                # Show history if requested (and if using --id)
                if args.show_history:
                    self._display_status_history(args.id, self.storage)
                    print()  # Add blank line for separation

                self._process_single_update(args.id, args.status, args.note, timestamp, self.storage)
            else:
                # Interactive mode for single order update
                self._process_interactive_update(args.status, args.note, args.show_history, timestamp, self.storage)

    def _display_status_history(self, order_id, storage):
        """Display the order's status history in tabular format."""
        order = storage.get_order(order_id)

        if not order:
            print(f"Order {order_id} not found")
            return False

        # Handle orders without status_history (backward compatibility)
        if not hasattr(order, 'status_history'):
            print(f"Order {order_id} - {order.customer_name}")
            print("No status history recorded. Only current status is available.")
            print(f"Current status: {order.status} (since order creation)")
            return True

        # Display order information and status history header
        print(f"Order {order_id} - {order.customer_name}")
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
        return True

    def _format_timestamp_for_display(self, timestamp):
        """Convert ISO timestamp to human-readable format."""
        dt = datetime.datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")

    def _display_status_change_summary(self, order_id, old_status, new_status, timestamp, note=None):
        """Display a summary of status change in a consistent format."""
        human_time = self._format_timestamp_for_display(timestamp)

        summary = f"Order ID {order_id}: Status changed from '{old_status}' to '{new_status}' at {human_time}"
        if note:
            summary += f" [Note: {note}]"

        print(summary)

    def _process_rollback(self, order_id, storage):
        order = storage.get_order(order_id)

        if not order:
            print(f"Order {order_id} not found")
            return

        # Check if there's a status history to roll back
        if not hasattr(order, 'status_history') or len(order.status_history) <= 1:
            print(f"Cannot roll back order {order_id}: No previous status exists")
            return

        # Display current status before rollback
        print(f"Order {order_id} - Current status: {order.status}")

        # Remove the most recent status entry
        most_recent = order.status_history.pop()

        # Get the previous status (now the last one in the list)
        previous_entry = order.status_history[-1]
        previous_status = previous_entry[1]

        # Update the order's current status
        current_status = order.status
        order.status = previous_status

        # Save the updated order
        storage.save_order(order)

        # Show rollback confirmation with details
        rolled_back_from = most_recent[1]
        rolled_back_to = previous_status

        print(f"Status rolled back from '{rolled_back_from}' to '{rolled_back_to}'")

        # If the rolled back entry had a note, display it
        if len(most_recent) > 2 and most_recent[2]:
            print(f"Removed note: {most_recent[2]}")

    def _process_batch_update(self, order_ids, status, note, timestamp, storage):
        # Batch update with validation for each order
        results = {"updated": [], "invalid_transition": [], "already_final": []}

        for order_id in order_ids:
            order = storage.get_order(order_id)
            if not order:
                print(f"Order {order_id} not found")
                continue

            # Display current status
            current_status = order.status
            print(f"Order {order_id} - Current status: {current_status}")

            # Check if already in final state
            if current_status in ["delivered", "canceled"]:
                print(f"  Cannot update: Order already in final state '{current_status}'")
                results["already_final"].append(order_id)
                continue

            # Check if transition is valid
            if status not in self.VALID_TRANSITIONS[current_status]:
                print(f"  Invalid transition: {current_status} → {status}")
                results["invalid_transition"].append(order_id)
                continue

            # Update the order status
            order.status = status

            # Initialize status_history if it doesn't exist (backward compatibility)
            if not hasattr(order, 'status_history'):
                order.status_history = [(order.order_time, "new", None)]

            # Add new status to history with optional note
            order.status_history.append((timestamp, status, note))

            # Save the updated order
            storage.save_order(order)

            # Display summary of the status change
            self._display_status_change_summary(order_id, current_status, status, timestamp, note)

            results["updated"].append(order_id)

        # Summary report
        print("\nSummary:")
        print(f"  Updated: {len(results['updated'])} orders")
        print(f"  Invalid transitions: {len(results['invalid_transition'])} orders")
        print(f"  Already in final state: {len(results['already_final'])} orders")

    def _process_single_update(self, order_id, status, note, timestamp, storage):
        order = storage.get_order(order_id)

        if not order:
            print(f"Order {order_id} not found")
            return

        # Get current status before update
        current_status = order.status
        print(f"Current status: {current_status}")

        # Check if already in final state
        if current_status in ["delivered", "canceled"]:
            print(f"Cannot update: Order already in final state '{current_status}'")
            return

        # Check if transition is valid
        if status not in self.VALID_TRANSITIONS[current_status]:
            print(f"Invalid transition: {current_status} → {status}")
            return

        # Update the order status
        order.status = status

        # Initialize status_history if it doesn't exist (backward compatibility)
        if not hasattr(order, 'status_history'):
            order.status_history = [(order.order_time, "new", None)]

        # Add new status to history with optional note
        order.status_history.append((timestamp, status, note))

        # Save the updated order
        storage.save_order(order)

        # Display summary of the status change
        self._display_status_change_summary(order_id, current_status, status, timestamp, note)

    def _process_interactive_update(self, status, note, show_history, timestamp, storage):
        order_id = input("Enter order ID: ").strip()

        # Show history if requested
        if show_history:
            self._display_status_history(order_id, storage)
            print()  # Add blank line for separation

        self._process_single_update(order_id, status, note, timestamp, storage)