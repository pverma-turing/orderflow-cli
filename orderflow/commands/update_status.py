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

    def execute(self, args):
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
                self._process_single_update(args.id, args.status, args.note, timestamp, self.storage)
            else:
                # Interactive mode for single order update
                self._process_interactive_update(args.status, args.note, timestamp, self.storage)

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
        order.status = previous_status

        # Save the updated order
        storage.update_order(order)

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
            print(f"Order {order_id} - Current status: {order.status}")

            # Check if already in final state
            if order.status in ["delivered", "canceled"]:
                print(f"  Cannot update: Order already in final state '{order.status}'")
                results["already_final"].append(order_id)
                continue

            # Check if transition is valid
            if status not in self.VALID_TRANSITIONS[order.status]:
                print(f"  Invalid transition: {order.status} → {status}")
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
            storage.update_order(order)

            # Show success message with note information
            status_msg = f"  Updated to: {status}"
            if note:
                status_msg += f" (Note: {note})"
            print(status_msg)

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

        # Display current status
        print(f"Current status: {order.status}")

        # Check if already in final state
        if order.status in ["delivered", "canceled"]:
            print(f"Cannot update: Order already in final state '{order.status}'")
            return

        # Check if transition is valid
        if status not in self.VALID_TRANSITIONS[order.status]:
            print(f"Invalid transition: {order.status} → {status}")
            return

        # Update the order status
        order.status = status

        # Initialize status_history if it doesn't exist (backward compatibility)
        if not hasattr(order, 'status_history'):
            order.status_history = [(order.order_time, "new", None)]

        # Add new status to history with optional note
        order.status_history.append((timestamp, status, note))

        # Save the updated order
        storage.update_order(order)

        # Show success message with note information
        status_msg = f"Order status updated to: {status}"
        if note:
            status_msg += f" (Note: {note})"
        print(status_msg)

    def _process_interactive_update(self, status, note, timestamp, storage):
        order_id = input("Enter order ID: ").strip()
        self._process_single_update(order_id, status, note, timestamp, storage)