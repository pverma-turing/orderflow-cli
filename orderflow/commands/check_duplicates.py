from orderflow.commands.base import Command
from tabulate import tabulate
from datetime import datetime, timedelta
import itertools
from collections import defaultdict


class CheckDuplicatesCommand(Command):
    """Command to identify potential duplicate orders"""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        # Time window parameter
        parser.add_argument(
            '--time-window',
            type=int,
            default=5,
            help='Time window in minutes to check for duplicates (default: 5)'
        )

        # Limit search to recent orders
        parser.add_argument(
            '--recent-days',
            type=int,
            default=1,
            help='Only check orders from the past N days (default: 1, use 0 for all orders)'
        )

        # Detailed options
        parser.add_argument(
            '--ignore-status',
            action='store_true',
            help='Ignore order status when checking for duplicates'
        )

        parser.add_argument(
            '--ignore-total',
            action='store_true',
            help='Ignore order total when checking for duplicates'
        )

        parser.add_argument(
            '--verbose',
            '-v',
            action='store_true',
            help='Show more detailed information about potential duplicates'
        )

        parser.add_argument(
            '--exact-match-only',
            action='store_true',
            help='Only consider exact matches (stricter definition of duplicates)'
        )

        # Add examples to epilog
        parser.epilog = """
Examples:
  # Basic duplicate check with default settings (5 minute window, past day)
  orderflow check-duplicates

  # Check for duplicates with a wider time window
  orderflow check-duplicates --time-window 15

  # Check all orders in the system
  orderflow check-duplicates --recent-days 0

  # Only consider exact matches (same customer, dishes, total)
  orderflow check-duplicates --exact-match-only

  # Show detailed information about potential duplicates
  orderflow check-duplicates --verbose
"""

    def execute(self, args):
        try:
            # Get all orders
            all_orders = self.storage.get_orders()

            if not all_orders:
                print("No orders found in the system.")
                return []

            # Filter by recency if needed
            orders_to_check = all_orders
            if args.recent_days > 0:
                cutoff_date = datetime.now() - timedelta(days=args.recent_days)
                orders_to_check = []

                for order in all_orders:
                    try:
                        order_dt = datetime.fromisoformat(order.order_time)
                        if order_dt >= cutoff_date:
                            orders_to_check.append(order)
                    except (ValueError, TypeError):
                        # Skip orders with unparseable dates
                        continue

            if not orders_to_check:
                print(f"No orders found in the past {args.recent_days} day(s).")
                return []

            # Find potential duplicates
            duplicate_groups = self._find_duplicate_groups(orders_to_check, args)

            # Display results
            if not duplicate_groups:
                print("No potential duplicate orders found.")
                return []

            # Display duplicate groups
            self._display_duplicate_groups(duplicate_groups, args)

            # Return all orders in duplicate groups
            return list(itertools.chain.from_iterable(duplicate_groups))

        except Exception as e:
            print(f"Error checking for duplicates: {str(e)}")
            return []

    def _find_duplicate_groups(self, orders, args):
        """Find groups of potential duplicate orders"""
        duplicate_groups = []
        time_window_seconds = args.time_window * 60

        # First, group orders by customer name
        customer_orders = defaultdict(list)
        for order in orders:
            customer_orders[order.customer_name.lower()].append(order)

        # For each customer, check for potential duplicates
        for customer_name, cust_orders in customer_orders.items():
            # Skip if only one order for this customer
            if len(cust_orders) <= 1:
                continue

            # Sort by order time
            try:
                # Try to sort by order time - skip customers with unparseable dates
                cust_orders.sort(key=lambda o: datetime.fromisoformat(o.order_time))
            except (ValueError, TypeError):
                continue

            # Check each pair of orders
            # Use a sliding window approach for efficiency with large datasets
            i = 0
            while i < len(cust_orders):
                current_order = cust_orders[i]
                current_dt = datetime.fromisoformat(current_order.order_time)

                # Start a potential duplicate group with the current order
                group = [current_order]
                is_duplicate_group = False

                # Look at subsequent orders within the time window
                j = i + 1
                while j < len(cust_orders):
                    next_order = cust_orders[j]
                    next_dt = datetime.fromisoformat(next_order.order_time)

                    # Check if within time window
                    time_diff = (next_dt - current_dt).total_seconds()
                    if time_diff > time_window_seconds:
                        # Past the window, no need to check further orders
                        break

                    # Check if dishes match (for old orders without quantities)
                    dishes_match = self._compare_dishes(current_order, next_order, args.exact_match_only)

                    # Check other criteria if needed
                    total_match = True
                    if not args.ignore_total and abs(current_order.order_total - next_order.order_total) > 0.01:
                        total_match = False

                    status_match = True
                    if not args.ignore_status and current_order.status != next_order.status:
                        status_match = False

                    # Determine if it's a duplicate based on our criteria
                    is_duplicate = dishes_match
                    if args.exact_match_only:
                        is_duplicate = is_duplicate and total_match and status_match

                    if is_duplicate:
                        group.append(next_order)
                        is_duplicate_group = True

                    j += 1

                # If we found duplicates, add the group
                if is_duplicate_group:
                    duplicate_groups.append(group)

                i += 1

        return duplicate_groups

    def _compare_dishes(self, order1, order2, exact_match=False):
        """Compare dishes between two orders to check for duplicates"""
        # Handle old-format orders without quantities
        if not hasattr(order1, 'dishes') or not hasattr(order2, 'dishes'):
            # Fall back to comparing dish names lists
            dish_names1 = set(order1.get_dish_names())
            dish_names2 = set(order2.get_dish_names())
            return dish_names1 == dish_names2

        # Get normalized dish lists with quantities
        dishes1 = self._normalize_dishes(order1.dishes)
        dishes2 = self._normalize_dishes(order2.dishes)

        # For exact match, both dish lists must be identical
        if exact_match:
            # Must have same number of unique dishes
            if len(dishes1) != len(dishes2):
                return False

            # Each dish must have the same quantity in both orders
            for dish_name, qty1 in dishes1.items():
                if dish_name not in dishes2 or dishes2[dish_name] != qty1:
                    return False

            return True
        else:
            # For relaxed match, check if the dish sets are the same
            # (ignoring quantities)
            return set(dishes1.keys()) == set(dishes2.keys())

    def _normalize_dishes(self, dishes):
        """Create a normalized dictionary of dish names to quantities"""
        result = {}
        for dish in dishes:
            name = dish['name'].lower().strip()
            qty = dish.get('quantity', 1)
            if name in result:
                result[name] += qty
            else:
                result[name] = qty
        return result

    def _display_duplicate_groups(self, duplicate_groups, args):
        """Display the duplicate groups in a readable format"""
        total_groups = len(duplicate_groups)
        total_orders = sum(len(group) for group in duplicate_groups)

        print(f"\nFound {total_groups} group(s) of potential duplicate orders ({total_orders} orders total)")

        # Process each group
        for i, group in enumerate(duplicate_groups, 1):
            print(f"\n{'-' * 40}")
            print(f"Duplicate Group #{i} - {len(group)} orders for {group[0].customer_name}")
            print(f"{'-' * 40}")

            # Create a table for this group
            table_data = []
            for order in group:
                # Format the date for better readability
                try:
                    dt = datetime.fromisoformat(order.order_time)
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    formatted_time = order.order_time

                # Format dishes
                dishes_str = order.get_formatted_dishes()
                if len(dishes_str) > 40:
                    dishes_str = dishes_str[:37] + "..."

                row = [
                    order.order_id[:8] + "...",
                    formatted_time,
                    dishes_str,
                    f"${order.order_total:.2f}",
                    order.status
                ]

                # Add more details in verbose mode
                if args.verbose:
                    tags_str = ", ".join(order.tags) if order.tags else "-"
                    if len(tags_str) > 15:
                        tags_str = tags_str[:12] + "..."

                    notes_str = order.notes if order.notes else "-"
                    if len(notes_str) > 15:
                        notes_str = notes_str[:12] + "..."

                    row.extend([tags_str, notes_str])

                table_data.append(row)

            # Display the table
            headers = ["Order ID", "Time", "Dishes", "Total", "Status"]
            if args.verbose:
                headers.extend(["Tags", "Notes"])

            print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Print summary
        print(f"\nSummary: Found {total_groups} group(s) with a total of {total_orders} potentially duplicate orders")
        print(f"Time window used: {args.time_window} minutes")
        if args.recent_days > 0:
            print(f"Only checked orders from the past {args.recent_days} day(s)")