import argparse
from orderflow.commands.base import Command
from tabulate import tabulate
from datetime import datetime, date, timedelta
from collections import Counter, defaultdict
import math
import sys


class DateValidator(argparse.Action):
    """Custom argparse action to validate date format"""

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            datetime.strptime(values, "%Y-%m-%d")
            setattr(namespace, self.dest, values)
        except ValueError:
            parser.error(f"{option_string} must be in YYYY-MM-DD format")


class ViewCommand(Command):
    """Command to view all orders with comprehensive filtering, pagination and reporting options"""

    VALID_STATUSES = ["new", "preparing", "delivered", "canceled"]
    DATE_FORMAT = "%Y-%m-%d"

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        # Sorting arguments
        sort_group = parser.add_argument_group('Sorting Options')
        sort_group.add_argument(
            '--sort-by',
            choices=['order_total', 'order_time'],
            default='order_time',
            help='Field to sort by (default: order_time)'
        )
        sort_group.add_argument(
            '--reverse',
            action='store_true',
            help='Reverse the sort order (default: False)'
        )

        # Status filtering
        status_group = parser.add_argument_group('Status Filtering')
        status_group.add_argument(
            '--status',
            choices=self.VALID_STATUSES,
            help=f'Filter orders by status (choices: {", ".join(self.VALID_STATUSES)})'
        )
        status_group.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active orders (exclude canceled)'
        )

        # Date filtering
        date_group = parser.add_argument_group('Date Filtering')
        date_group.add_argument(
            '--from-date',
            action=DateValidator,
            help='Show orders from this date (YYYY-MM-DD format)'
        )
        date_group.add_argument(
            '--to-date',
            action=DateValidator,
            help='Show orders until this date (YYYY-MM-DD format)'
        )
        date_group.add_argument(
            '--today',
            action='store_true',
            help='Show only today\'s orders'
        )

        # Content filtering
        content_group = parser.add_argument_group('Content Filtering')
        content_group.add_argument(
            '--dish',
            help='Filter by dish name (partial matches allowed)'
        )
        content_group.add_argument(
            '--customer',
            help='Filter by customer name (partial matches allowed)'
        )
        content_group.add_argument(
            '--tag',
            help='Filter by tag (partial matches allowed)'
        )
        content_group.add_argument(
            '--with-notes',
            action='store_true',
            help='Show only orders with notes'
        )
        content_group.add_argument(
            '--without-notes',
            action='store_true',
            help='Show only orders without notes'
        )

        # Summary reports
        report_group = parser.add_argument_group('Summary Reports')
        report_group.add_argument(
            '--top-dishes',
            action='store_true',
            help='Display the top 5 most ordered dishes'
        )
        report_group.add_argument(
            '--top-customers',
            action='store_true',
            help='Display the top 5 customers by number of orders'
        )

        # Pagination options
        pagination_group = parser.add_argument_group('Pagination')
        pagination_group.add_argument(
            '--page',
            type=int,
            default=1,
            help='Page number to display (default: 1)'
        )
        pagination_group.add_argument(
            '--page-size',
            type=int,
            default=10,
            help='Number of orders per page (default: 10, use 0 for no pagination)'
        )

        # Add examples to epilog
        parser.epilog = """
Examples:
  # Basic usage - view all orders
  orderflow view

  # Sort by total (highest first)
  orderflow view --sort-by order_total --reverse

  # Filter by date range
  orderflow view --from-date 2023-01-01 --to-date 2023-01-31

  # Today's orders with a specific status
  orderflow view --today --status delivered

  # Filter by dish and tag
  orderflow view --dish "Pizza" --tag "delivery"

  # View top customers for a specific time period
  orderflow view --from-date 2023-01-01 --top-customers

  # Combine multiple filters
  orderflow view --customer "Smith" --status preparing --active-only

  # Paginate through large result sets
  orderflow view --page 2 --page-size 20
"""

    def execute(self, args):
        try:
            # Validate contradictory args
            if args.with_notes and args.without_notes:
                print("Error: Cannot specify both --with-notes and --without-notes")
                return []

            # Validate pagination parameters
            if args.page < 1:
                print("Error: Page number must be 1 or greater")
                return []

            if args.page_size < 0:
                print("Error: Page size must be 0 (no pagination) or a positive number")
                return []

            # Get all orders
            all_orders = self.storage.get_orders()

            if not all_orders:
                print("No orders found in the storage. Use 'orderflow add' to create new orders.")
                return []

            # Apply filters
            filtered_orders = self._apply_filters(all_orders, args)

            # Sort orders if we're displaying the orders list
            if not (args.top_dishes or args.top_customers) or len(filtered_orders) > 0:
                if args.sort_by == 'order_total':
                    filtered_orders.sort(key=lambda x: x.order_total, reverse=args.reverse)
                else:  # order_time
                    filtered_orders.sort(key=lambda x: x.order_time, reverse=args.reverse)

            # Handle summary reports (these can run even if filtered_orders is empty)
            if args.top_dishes:
                self._display_top_dishes(all_orders, filtered_orders)
                # If only summary is requested, return after displaying it
                if not filtered_orders or (args.top_dishes and args.top_customers and not any(
                        [args.status, args.active_only, args.from_date, args.to_date,
                         args.today, args.dish, args.customer, args.tag,
                         args.with_notes, args.without_notes])):
                    return filtered_orders

            if args.top_customers:
                self._display_top_customers(all_orders, filtered_orders)
                # If only summary is requested, return after displaying it
                if not filtered_orders or (args.top_dishes and args.top_customers and not any(
                        [args.status, args.active_only, args.from_date, args.to_date,
                         args.today, args.dish, args.customer, args.tag,
                         args.with_notes, args.without_notes])):
                    return filtered_orders

            # Display orders table if we have orders and not only showing summary reports
            if not filtered_orders:
                print("No orders found matching the criteria.")
                return []

            # Apply pagination if enabled
            paginated_orders = filtered_orders
            if args.page_size > 0:
                # Calculate pagination indexes
                total_pages = math.ceil(len(filtered_orders) / args.page_size)
                start_idx = (args.page - 1) * args.page_size
                end_idx = start_idx + args.page_size

                # Validate page number
                if args.page > total_pages:
                    print(f"Error: Page {args.page} does not exist. Maximum page is {total_pages}.")
                    return []

                paginated_orders = filtered_orders[start_idx:end_idx]

                # Display pagination info
                print(f"Showing page {args.page} of {total_pages} ({len(filtered_orders)} total orders)")

            # Display orders table
            self._display_orders_table(paginated_orders)

            # Display status counts for all filtered orders
            self._display_status_counts(all_orders, filtered_orders)

            # Display revenue statistics for all filtered orders
            self._display_revenue_stats(filtered_orders)

            # Display tag-based revenue breakdown
            self._display_tag_revenue_breakdown(filtered_orders)

            return filtered_orders

        except ValueError as e:
            print(f"Error: {str(e)}")
            return []
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return []

    def _apply_filters(self, orders, args):
        """Apply all filters to the orders list"""
        filtered_orders = []

        # Parse date filters
        from_date = None
        to_date = None

        # Handle --today shortcut
        if args.today:
            today = date.today()
            from_date = today
            to_date = today
        else:
            # Parse --from-date if provided
            if args.from_date:
                try:
                    from_date = datetime.strptime(args.from_date, self.DATE_FORMAT).date()
                except ValueError:
                    print(f"Invalid from-date format. Please use {self.DATE_FORMAT}")
                    return []

            # Parse --to-date if provided
            if args.to_date:
                try:
                    to_date = datetime.strptime(args.to_date, self.DATE_FORMAT).date()
                except ValueError:
                    print(f"Invalid to-date format. Please use {self.DATE_FORMAT}")
                    return []

        for order in orders:
            # Status filter
            if args.status and order.status != args.status:
                continue

            # Active-only filter (exclude canceled)
            if args.active_only and order.status == "canceled":
                continue

            if args.dish:
                # Check if any dish in the order matches the filter
                if not order.has_dish(args.dish):
                    continue

            # Date filters
            order_datetime = None
            try:
                order_datetime = datetime.fromisoformat(order.order_time)
            except (ValueError, TypeError):
                # Skip orders with invalid date format
                continue

            order_date = order_datetime.date()

            # From date filter
            if from_date and order_date < from_date:
                continue

            # To date filter
            if to_date and order_date > to_date:
                continue

            # Dish filter (partial match)
            if args.dish:
                # Check if any dish in the order matches the filter
                dish_match = False
                for dish in order.dish_names:
                    if args.dish.lower() in dish.lower():
                        dish_match = True
                        break
                if not dish_match:
                    continue

            # Customer filter (partial match)
            if args.customer and args.customer.lower() not in order.customer_name.lower():
                continue

            # Tag filter (partial match)
            if args.tag:
                # Check if any tag in the order matches the filter
                tag_match = False
                for tag in order.tags:
                    if args.tag.lower() in tag.lower():
                        tag_match = True
                        break
                if not tag_match:
                    continue

            # Notes filters
            if args.with_notes and not order.notes.strip():
                continue
            if args.without_notes and order.notes.strip():
                continue

            # Order passes all filters
            filtered_orders.append(order)

        return filtered_orders

    def _display_orders_table(self, orders):
        """Display orders in a formatted table with dish quantities"""
        if not orders:
            return

        table_data = []
        for order in orders:
            # Format the date for better readability
            try:
                dt = datetime.fromisoformat(order.order_time)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                formatted_time = order.order_time

            # Format dishes with quantities
            dishes_str = order.get_formatted_dishes()
            if len(dishes_str) > 30:
                dishes_str = dishes_str[:27] + "..."

            # Format tags and truncate notes if needed
            tags_str = ", ".join(order.tags) if order.tags else ""
            if len(tags_str) > 20:  # Truncate long tags
                tags_str = tags_str[:17] + "..."

            notes_str = order.notes if order.notes else ""
            if len(notes_str) > 30:  # Truncate long notes
                notes_str = notes_str[:27] + "..."

            table_data.append([
                order.order_id[:8] + "...",  # Truncate UUID for display
                order.customer_name[:20] + "..." if len(order.customer_name) > 20 else order.customer_name,
                dishes_str,
                f"${order.order_total:.2f}",
                order.status,
                formatted_time,
                tags_str,
                notes_str
            ])

        # Get terminal width for potential adaptive formatting
        try:
            term_width = sys.stdout.get_terminal_size().columns
        except (AttributeError, OSError):
            term_width = 120  # Default for non-terminal environments

        # Choose table format based on available width
        table_format = "grid" if term_width >= 120 else "simple"

        # Display table with appropriate width handling
        headers = ["Order ID", "Customer", "Dishes", "Total", "Status", "Time", "Tags", "Notes"]
        print(tabulate(table_data, headers=headers, tablefmt=table_format))

    def _display_status_counts(self, all_orders, filtered_orders):
        """Display count summary of orders by status"""
        # Count orders by status from the filtered set
        status_counts = Counter(order.status for order in filtered_orders)

        # Ensure all valid statuses are represented
        for status in self.VALID_STATUSES:
            if status not in status_counts:
                status_counts[status] = 0

        # Display counts
        print("\nOrder Status Summary (filtered):")
        for status in self.VALID_STATUSES:
            print(f"  {status.capitalize()}: {status_counts[status]}")

        filtered_total = sum(status_counts.values())
        all_total = len(all_orders)

        # Display totals
        print(f"  Total (filtered): {filtered_total}")
        if filtered_total != all_total:
            print(f"  Total (all orders): {all_total}")

    def _display_revenue_stats(self, orders):
        """Display revenue statistics for the filtered orders"""
        if not orders:
            return

        # Calculate total revenue
        total_revenue = sum(order.order_total for order in orders)

        # Calculate average order value
        avg_order_value = total_revenue / len(orders)

        # Display revenue stats
        print("\nRevenue Statistics:")
        print(f"  Total Orders: {len(orders)}")
        print(f"  Total Revenue: ${total_revenue:.2f}")
        print(f"  Average Order Value: ${avg_order_value:.2f}")

        # Calculate revenue by status
        status_revenue = {}
        for status in self.VALID_STATUSES:
            status_orders = [order for order in orders if order.status == status]
            if status_orders:
                status_revenue[status] = sum(order.order_total for order in status_orders)
            else:
                status_revenue[status] = 0.0

        print("\nRevenue by Status:")
        for status in self.VALID_STATUSES:
            print(f"  {status.capitalize()}: ${status_revenue[status]:.2f}")

    def _display_tag_revenue_breakdown(self, orders):
        """Display revenue breakdown by tags for filtered orders"""
        if not orders:
            return

        # Count orders and sum revenue by tag
        tag_stats = defaultdict(lambda: {'count': 0, 'revenue': 0.0})
        orders_with_tags = 0
        tag_revenue_total = 0.0

        for order in orders:
            if order.tags:
                orders_with_tags += 1
                for tag in order.tags:
                    tag_stats[tag]['count'] += 1
                    tag_stats[tag]['revenue'] += order.order_total
                    tag_revenue_total += order.order_total

        # Display tag revenue breakdown if applicable
        if tag_stats:
            print("\nRevenue Breakdown by Tag:")

            # Prepare table data
            tag_data = []
            for tag, stats in sorted(tag_stats.items(), key=lambda x: x[1]['revenue'], reverse=True):
                tag_data.append([
                    tag,
                    stats['count'],
                    f"${stats['revenue']:.2f}",
                    f"{(stats['revenue'] / tag_revenue_total) * 100:.1f}%"
                ])

            # Display as table
            headers = ["Tag", "Orders", "Revenue", "% of Tagged Revenue"]
            print(tabulate(tag_data, headers=headers, tablefmt="simple"))

            # Handle orders with multiple tags being counted multiple times
            if orders_with_tags > 0:
                print(
                    f"\nNote: {orders_with_tags} orders have tags. Orders with multiple tags are counted for each tag.")
        else:
            print("\nNo tagged orders found in the filtered results.")

    def _display_top_dishes(self, all_orders, filtered_orders):
        """Display the top 5 most ordered dishes with quantities and accurate revenue"""
        orders_to_analyze = filtered_orders if filtered_orders else all_orders

        # Create dish counters and revenue trackers
        dish_quantities = {}
        dish_revenue = {}

        # Process all orders
        for order in orders_to_analyze:
            # Get the proportional revenue for each dish in this order
            dish_revenues = order.calculate_dish_revenue()

            # Add up quantities and revenue for each dish
            for dish in order.dishes:
                name = dish['name']
                quantity = dish['quantity']

                # Update quantity counts
                if name not in dish_quantities:
                    dish_quantities[name] = 0
                dish_quantities[name] += quantity

                # Update revenue for each dish
                if name not in dish_revenue:
                    dish_revenue[name] = 0
                dish_revenue[name] += dish_revenues.get(name, 0)

        # Sort dishes by quantity ordered
        top_dishes = sorted(
            dish_quantities.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Display the results
        print("\nTop 5 Most Ordered Dishes:")
        if not top_dishes:
            print("  No dishes found for the given criteria.")
            return

        dish_data = []
        for dish_name, quantity in top_dishes:
            revenue = dish_revenue.get(dish_name, 0)
            dish_data.append([
                dish_name,
                quantity,
                f"${revenue:.2f}",
                f"${revenue / quantity:.2f}" if quantity > 0 else "$0.00"
            ])

        # Display table
        headers = ["Dish Name", "Quantity", "Total Revenue", "Avg. Per Unit"]
        print(tabulate(dish_data, headers=headers, tablefmt="grid"))

    def _display_top_customers(self, all_orders, filtered_orders):
        """Display the top 5 customers by number of orders"""
        orders_to_analyze = filtered_orders if filtered_orders else all_orders

        # Count orders by customer
        customer_orders = {}
        for order in orders_to_analyze:
            if order.customer_name not in customer_orders:
                customer_orders[order.customer_name] = []
            customer_orders[order.customer_name].append(order)

        # Sort customers by order count
        sorted_customers = sorted(
            customer_orders.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]  # Take top 5

        # Display the results
        print("\nTop 5 Customers by Number of Orders:")
        if not sorted_customers:
            print("  No customers found for the given criteria.")
            return

        customer_data = []
        for customer_name, orders in sorted_customers:
            order_count = len(orders)
            total_spent = sum(order.order_total for order in orders)
            avg_order_value = total_spent / order_count

            customer_data.append([
                customer_name,
                order_count,
                f"${total_spent:.2f}",
                f"${avg_order_value:.2f}"
            ])

        # Display table
        headers = ["Customer Name", "Order Count", "Total Spent", "Avg Order"]
        print(tabulate(customer_data, headers=headers, tablefmt="grid"))