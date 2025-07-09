import argparse
import shutil

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

        report_group.add_argument("--dish-breakdown", action="store_true",
                            help="Show complete breakdown of all dishes in matching orders sorted by revenue")

        # New tags summary flag
        report_group.add_argument("--top-tags", action="store_true",
                                  help="Summarize order volume and revenue by tags across matching orders")

        # New sorting control flag
        report_group.add_argument("--report-sort",
                            help="Control sorting of summary reports: 'revenue', 'count', 'quantity', 'avg', 'total'")

        # New customer summary flag
        report_group.add_argument("--customer-summary", action="store_true",
                            help="Show a full alphabetical list of customer order statistics")

        report_group.add_argument("--avg-dish-value", action="store_true",
                            help="Show average revenue per unit sold for each dish across filtered orders")

        # New day summary flag
        report_group.add_argument("--day-summary", action="store_true",
                            help="Show revenue trends by day for the filtered orders")

        report_group.add_argument("--hourly-distribution", action="store_true",
                            help="Show order distribution by hour of day (0-23)")

        report_group.add_argument("--cancel-rate", action="store_true",
                            help="Show percentage of canceled orders within the filtered dataset")

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
                self._display_top_dishes(all_orders, filtered_orders, args.report_sort)
                # If only summary is requested, return after displaying it
                if not filtered_orders or (args.top_dishes and args.top_customers and not any(
                        [args.status, args.active_only, args.from_date, args.to_date,
                         args.today, args.dish, args.customer, args.tag,
                         args.with_notes, args.without_notes])):
                    return filtered_orders

            if args.top_customers:
                self._display_top_customers(all_orders, filtered_orders, args.report_sort)
                # If only summary is requested, return after displaying it
                if not filtered_orders or (args.top_dishes and args.top_customers and not any(
                        [args.status, args.active_only, args.from_date, args.to_date,
                         args.today, args.dish, args.customer, args.tag,
                         args.with_notes, args.without_notes])):
                    return filtered_orders

            if args.dish_breakdown:
                self._display_dish_breakdown(filtered_orders, "", args.report_sort)

            if args.top_tags:
                self._display_top_tags(filtered_orders, "", args.report_sort)

            if args.customer_summary:
                self._display_customer_summary(filtered_orders, "")

            if args.day_summary:
                self._display_day_summary(filtered_orders, "")

            if args.avg_dish_value:
                self._display_avg_dish_value(filtered_orders, "")

            if args.hourly_distribution:
                self._display_hourly_distribution(filtered_orders, "")

            if args.cancel_rate:
                self._display_cancel_rate(filtered_orders, "")

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

    def _display_top_dishes(self, all_orders, filtered_orders, sort_by=None):
        """Display the top 5 most ordered dishes with quantities and accurate revenue"""
        orders_to_analyze = filtered_orders if filtered_orders else all_orders
        valid_sorts = ["quantity", "revenue"]
        default_sort = "quantity"
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

        # If sort_by is specified but invalid, show error and use default
        if sort_by and sort_by not in valid_sorts:
            print(
                f"Error: Invalid sort option '{sort_by}' for dish report. Valid options are: {', '.join(valid_sorts)}")
            print(f"Using default sort: '{default_sort}'\n")
            sort_by = default_sort

        # If sort_by not specified, use default
        if not sort_by:
            sort_by = default_sort
        idx = valid_sorts.index(sort_by) +1
        dish_data.sort(key=lambda x: x[idx], reverse=True)
        # Display table
        headers = ["Dish Name", "Quantity", "Total Revenue", "Avg. Per Unit"]
        print(tabulate(dish_data, headers=headers, tablefmt="grid"))

    def _display_top_customers(self, all_orders, filtered_orders, sort_by=None):
        """Display the top 5 customers by number of orders"""
        orders_to_analyze = filtered_orders if filtered_orders else all_orders
        # Validate sort parameter for customers
        valid_sorts = ["count", "total", "avg"]
        default_sort = "count"

        # If sort_by is specified but invalid, show error and use default
        if sort_by and sort_by not in valid_sorts:
            print(
                f"Error: Invalid sort option '{sort_by}' for customer report. Valid options are: {', '.join(valid_sorts)}")
            print(f"Using default sort: '{default_sort}'\n")
            sort_by = default_sort

        # If sort_by not specified, use default
        if not sort_by:
            sort_by = default_sort

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

        idx = valid_sorts.index(sort_by) + 1
        customer_data.sort(key=lambda x: x[idx], reverse=True)

        # Display table
        headers = ["Customer Name", "Order Count", "Total Spent", "Avg Order"]
        print(tabulate(customer_data, headers=headers, tablefmt="grid"))

    def _should_use_grid_format(self):
        """Determine if grid format should be used based on terminal width."""
        try:
            columns, _ = shutil.get_terminal_size()
            return columns >= 100  # Use grid format for wider terminals
        except (AttributeError, OSError):
            return False

    def _display_dish_breakdown(self, orders, filter_description, sort_by=None):
        """Display complete breakdown of all dishes ordered, sorted by revenue."""
        # Validate sort parameter for dish breakdown
        valid_sorts = ["revenue", "quantity"]
        default_sort = "revenue"

        # If sort_by is specified but invalid, show error and use default
        if sort_by and sort_by not in valid_sorts:
            print(
                f"Error: Invalid sort option '{sort_by}' for dish breakdown. Valid options are: {', '.join(valid_sorts)}")
            print(f"Using default sort: '{default_sort}'\n")
            sort_by = default_sort

        # If sort_by not specified, use default
        if not sort_by:
            sort_by = default_sort

        # Aggregate dish data (reusing logic from _display_top_dishes)
        dish_data = {}
        total_revenue = 0.0

        # First pass - collect dish data
        for order in orders:
            for dish_item in order.dishes:
                try:
                    # Parse dish format (Dish Name:Quantity)
                    dish_name = dish_item['name']
                    quantity = dish_item['quantity']

                    if not dish_name:
                        continue

                    if dish_name not in dish_data:
                        dish_data[dish_name] = {"quantity": 0, "revenue": 0.0}

                    dish_data[dish_name]["quantity"] += quantity

                    # Estimate revenue based on proportion of the total order
                    total_qty_in_order = sum(int(d.split(":")[1].strip()) if ":" in d else 1 for d in order.dishes)
                    dish_proportion = quantity / total_qty_in_order if total_qty_in_order > 0 else 0
                    dish_revenue = order.order_total * dish_proportion

                    dish_data[dish_name]["revenue"] += dish_revenue
                    total_revenue += dish_revenue

                except (IndexError, ValueError, ZeroDivisionError):
                    # Skip malformed dish entries
                    continue

        # Create filter message
        filter_msg = f" (filtered by: {filter_description})" if filter_description else ""

        # Display the table header
        print(f"\nComplete Dish Breakdown{filter_msg}")
        if not dish_data:
            print("No dish data available for the current filters.")
            return

        # Prepare the table data sorted by revenue (descending)
        table_data = []
        for dish_name, data in sorted(dish_data.items(), key=lambda x: x[1]["revenue"], reverse=True):
            quantity = data["quantity"]
            revenue = data["revenue"]
            avg_revenue = revenue / quantity if quantity > 0 else 0
            revenue_percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0

            table_data.append([
                dish_name,
                quantity,
                f"${revenue:.2f}",
                f"${avg_revenue:.2f}",
                f"{revenue_percentage:.2f}%"
            ])

        idx = valid_sorts.index(sort_by) + 1
        table_data.sort(key=lambda x: x[idx], reverse=True)

        headers = ["Dish Name", "Quantity", "Total Revenue", "Avg Revenue/Unit", "% of Revenue"]

        # Use the same tabulate format as the main order listing
        use_grid = self._should_use_grid_format()
        print(tabulate(table_data, headers=headers, tablefmt="grid" if use_grid else "simple"))
        print(f"\nTotal Revenue: ${total_revenue:.2f}")

    def _display_top_tags(self, orders, filter_description, sort_by=None):
        """Display summary of order volume and revenue by tags."""
        # Aggregate tag data
        # Validate sort parameter for tags
        valid_sorts = ["revenue", "count"]
        default_sort = "revenue"

        # If sort_by is specified but invalid, show error and use default
        if sort_by and sort_by not in valid_sorts:
            print(f"Error: Invalid sort option '{sort_by}' for tag report. Valid options are: {', '.join(valid_sorts)}")
            print(f"Using default sort: '{default_sort}'\n")
            sort_by = default_sort

        # If sort_by not specified, use default
        if not sort_by:
            sort_by = default_sort

        tag_data = {}
        total_revenue = 0.0

        # First pass - collect tag data
        for order in orders:
            # Skip orders without tags
            if not order.tags or not isinstance(order.tags, list):
                continue

            # Add order revenue to total (will be used for percentage calculation)
            total_revenue += order.order_total

            # Process each tag in the order
            for tag in order.tags:
                # Skip empty tags
                if not tag or not isinstance(tag, str):
                    continue

                # Normalize tag (case-insensitive aggregation)
                normalized_tag = tag.lower().strip()
                if not normalized_tag:
                    continue

                # Initialize tag data if not already present
                if normalized_tag not in tag_data:
                    tag_data[normalized_tag] = {
                        "order_count": 0,
                        "revenue": 0.0,
                        "display_name": tag  # Keep original capitalization for display
                    }

                # Update tag data
                tag_data[normalized_tag]["order_count"] += 1
                tag_data[normalized_tag]["revenue"] += order.order_total

                # Update display name with most common capitalization
                # This keeps the most frequently used capitalization
                if tag != tag_data[normalized_tag]["display_name"]:
                    # Simple heuristic: longer tag is likely more intentional formatting
                    if len(tag) > len(tag_data[normalized_tag]["display_name"]):
                        tag_data[normalized_tag]["display_name"] = tag

        # Create filter message
        filter_msg = f" (filtered by: {filter_description})" if filter_description else ""

        # Display the table header
        print(f"\nTag Summary{filter_msg}")

        if not tag_data:
            print("No tagged orders found with the current filters.")
            return

        # Prepare the table data sorted by revenue (descending)
        table_data = []
        for normalized_tag, data in sorted(tag_data.items(), key=lambda x: x[1]["revenue"], reverse=True):
            order_count = data["order_count"]
            revenue = data["revenue"]
            revenue_percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0

            # Use the preserved display name for better readability
            display_name = data["display_name"]

            table_data.append([
                display_name,
                order_count,
                f"${revenue:.2f}",
                f"{revenue_percentage:.2f}%"
            ])

        idx = valid_sorts.index(sort_by) + 1
        table_data.sort(key=lambda x: x[idx], reverse=True)
        headers = ["Tag", "Order Count", "Total Revenue", "% of Revenue"]

        # Use the same tabulate format as the main order listing
        use_grid = self._should_use_grid_format()
        print(tabulate(table_data, headers=headers, tablefmt="grid" if use_grid else "simple"))
        print(f"\nTotal Revenue: ${total_revenue:.2f}")

    def _display_customer_summary(self, orders, filter_description):
        """Display a comprehensive alphabetical list of all customers with their order statistics."""
        # Aggregate customer data
        customer_data = {}

        # First pass - collect customer data
        for order in orders:
            customer_name = order.customer_name
            if not customer_name or not isinstance(customer_name, str):
                continue  # Skip orders with no customer name

            # Initialize customer data if not already present
            if customer_name not in customer_data:
                customer_data[customer_name] = {
                    "order_count": 0,
                    "total_spent": 0.0
                }

            # Update customer data
            customer_data[customer_name]["order_count"] += 1
            customer_data[customer_name]["total_spent"] += order.order_total

        # Create filter message
        filter_msg = f" (filtered by: {filter_description})" if filter_description else ""

        # Display the table header
        print(f"\nCustomer Order Summary{filter_msg}")

        if not customer_data:
            print("No customer data available for the current filters.")
            return

        # Prepare the table data sorted alphabetically by customer name
        table_data = []
        for customer_name in sorted(customer_data.keys()):
            data = customer_data[customer_name]
            order_count = data["order_count"]
            total_spent = data["total_spent"]
            avg_order_value = total_spent / order_count if order_count > 0 else 0

            table_data.append([
                customer_name,
                order_count,
                f"${total_spent:.2f}",
                f"${avg_order_value:.2f}"
            ])

        headers = ["Customer Name", "Order Count", "Total Spent", "Avg Order Value"]

        # Use the same tabulate format as other reports
        use_grid = self._should_use_grid_format()
        print(tabulate(table_data, headers=headers, tablefmt="grid" if use_grid else "simple"))

        # Add a summary footer
        total_customers = len(customer_data)
        total_orders = sum(data["order_count"] for data in customer_data.values())
        total_revenue = sum(data["total_spent"] for data in customer_data.values())

        print(f"\nSummary: {total_customers} customers, {total_orders} orders, ${total_revenue:.2f} total revenue")

    def _display_day_summary(self, orders, filter_description):
        """Display revenue trends by day for the filtered orders."""
        from datetime import datetime

        # Dictionary to store data aggregated by day
        daily_data = {}

        # First pass - collect data by day
        for order in orders:
            # Skip orders without a valid order_time
            if not hasattr(order, 'order_time') or not order.order_time:
                continue

            # Convert order_time to datetime if it's a string
            order_date = order.order_time
            if isinstance(order_date, str):
                try:
                    # Try to parse the date string (handle different formats)
                    order_date = datetime.strptime(order_date.split(' ')[0], '%Y-%m-%d')
                except (ValueError, IndexError):
                    try:
                        order_date = datetime.strptime(order_date.split('T')[0], '%Y-%m-%d')
                    except (ValueError, IndexError):
                        # Skip orders with unparseable dates
                        continue

            # Extract just the date part (YYYY-MM-DD)
            date_key = order_date.strftime('%Y-%m-%d') if hasattr(order_date, 'strftime') else \
            str(order_date).split(' ')[0]

            # Initialize day data if not already present
            if date_key not in daily_data:
                daily_data[date_key] = {
                    "order_count": 0,
                    "total_revenue": 0.0
                }

            # Update daily data
            daily_data[date_key]["order_count"] += 1
            daily_data[date_key]["total_revenue"] += order.order_total

        # Create filter message
        filter_msg = f" (filtered by: {filter_description})" if filter_description else ""

        # Display the table header
        print(f"\nDaily Revenue Summary{filter_msg}")

        if not daily_data:
            print("No order data available for the current filters.")
            return

        # Prepare the table data sorted by date (ascending)
        table_data = []
        for date_key in sorted(daily_data.keys()):
            data = daily_data[date_key]
            order_count = data["order_count"]
            total_revenue = data["total_revenue"]
            avg_order_value = total_revenue / order_count if order_count > 0 else 0

            table_data.append([
                date_key,
                order_count,
                f"${total_revenue:.2f}",
                f"${avg_order_value:.2f}"
            ])

        headers = ["Date", "Order Count", "Total Revenue", "Avg Order Value"]

        # Use the same tabulate format as other reports
        use_grid = self._should_use_grid_format()
        print(tabulate(table_data, headers=headers, tablefmt="grid" if use_grid else "simple"))

        # Add a summary footer
        total_days = len(daily_data)
        total_orders = sum(data["order_count"] for data in daily_data.values())
        total_revenue = sum(data["total_revenue"] for data in daily_data.values())
        overall_avg = total_revenue / total_orders if total_orders > 0 else 0

        print(f"\nSummary: {total_days} days, {total_orders} orders, ${total_revenue:.2f} total revenue")
        print(f"Overall average order value: ${overall_avg:.2f}")

    def _display_avg_dish_value(self, orders, filter_description):
        """Display average revenue per unit for each dish across filtered orders."""
        # Aggregate dish data
        dish_data = {}

        # First pass - collect dish data
        for order in orders:
            for dish_item in order.dishes:
                try:
                    # Parse dish format (Dish Name:Quantity)
                    dish_name = dish_item['name']
                    quantity = dish_item['quantity']

                    if not dish_name:
                        continue

                    if dish_name not in dish_data:
                        dish_data[dish_name] = {"quantity": 0, "revenue": 0.0}

                    dish_data[dish_name]["quantity"] += quantity

                    # Estimate revenue based on proportion of the total order
                    total_qty_in_order = sum(int(d.split(":")[1].strip()) if ":" in d else 1 for d in order.dishes)
                    dish_proportion = quantity / total_qty_in_order if total_qty_in_order > 0 else 0
                    dish_revenue = order.order_total * dish_proportion

                    dish_data[dish_name]["revenue"] += dish_revenue

                except (IndexError, ValueError, ZeroDivisionError):
                    # Skip malformed dish entries
                    continue

        # Create filter message
        filter_msg = f" (filtered by: {filter_description})" if filter_description else ""

        # Display the table header
        print(f"\nAverage Dish Value Report{filter_msg}")

        if not dish_data:
            print("No dish data available for the current filters.")
            return

        # Calculate average value per unit for each dish
        for dish_name, data in dish_data.items():
            quantity = data["quantity"]
            revenue = data["revenue"]
            data["avg_value"] = revenue / quantity if quantity > 0 else 0

        # Prepare the table data sorted by average value (descending)
        table_data = []
        for dish_name, data in sorted(dish_data.items(), key=lambda x: x[1]["avg_value"], reverse=True):
            quantity = data["quantity"]
            revenue = data["revenue"]
            avg_value = data["avg_value"]

            table_data.append([
                dish_name,
                quantity,
                f"${revenue:.2f}",
                f"${avg_value:.2f}"
            ])

        headers = ["Dish Name", "Quantity Sold", "Total Revenue", "Avg Revenue/Unit"]

        # Use grid format for the table
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Add a summary footer
        total_dishes = len(dish_data)
        total_quantity = sum(data["quantity"] for data in dish_data.values())
        total_revenue = sum(data["revenue"] for data in dish_data.values())
        overall_avg_value = total_revenue / total_quantity if total_quantity > 0 else 0

        print(
            f"\nSummary: {total_dishes} unique dishes, {total_quantity} units sold, ${total_revenue:.2f} total revenue")
        print(f"Overall average revenue per unit: ${overall_avg_value:.2f}")

    def _display_hourly_distribution(self, orders, filter_description):
        """Display order distribution by hour of day."""
        from datetime import datetime

        # Dictionary to store data aggregated by hour
        hourly_data = {}

        # First pass - collect data by hour
        for order in orders:
            # Skip orders without a valid order_time
            if not hasattr(order, 'order_time') or not order.order_time:
                continue

            # Convert order_time to datetime if it's a string
            order_time = order.order_time
            if isinstance(order_time, str):
                try:
                    # Try to parse the datetime string
                    if 'T' in order_time:
                        # ISO format (2023-01-01T12:34:56)
                        order_time = datetime.fromisoformat(order_time.replace('Z', '+00:00'))
                    else:
                        # Space-delimited format (2023-01-01 12:34:56)
                        order_time = datetime.strptime(order_time, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    # Skip orders with unparseable timestamps
                    continue

            # Extract hour component (0-23)
            hour = order_time.hour if hasattr(order_time, 'hour') else None
            if hour is None:
                continue

            # Initialize hour data if not already present
            if hour not in hourly_data:
                hourly_data[hour] = {
                    "order_count": 0,
                    "total_revenue": 0.0
                }

            # Update hourly data
            hourly_data[hour]["order_count"] += 1
            hourly_data[hour]["total_revenue"] += order.order_total

        # Create filter message
        filter_msg = f" (filtered by: {filter_description})" if filter_description else ""

        # Display the table header
        print(f"\nHourly Order Distribution{filter_msg}")

        if not hourly_data:
            print("No order data available for the current filters.")
            return

        # Prepare the table data sorted by hour (ascending)
        table_data = []
        for hour in sorted(hourly_data.keys()):
            data = hourly_data[hour]
            order_count = data["order_count"]
            total_revenue = data["total_revenue"]
            avg_order_value = total_revenue / order_count if order_count > 0 else 0

            # Format hour for display (e.g., "07:00 - 07:59" for hour 7)
            hour_display = f"{hour:02d}:00 - {hour:02d}:59"

            table_data.append([
                hour_display,
                order_count,
                f"${total_revenue:.2f}",
                f"${avg_order_value:.2f}"
            ])

        headers = ["Hour of Day", "Order Count", "Total Revenue", "Avg Order Value"]

        # Use grid format for the table
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Add a summary footer
        total_hours = len(hourly_data)
        total_orders = sum(data["order_count"] for data in hourly_data.values())
        total_revenue = sum(data["total_revenue"] for data in hourly_data.values())

        peak_hour = max(hourly_data.items(), key=lambda x: x[1]["order_count"])[0]
        peak_hour_display = f"{peak_hour:02d}:00 - {peak_hour:02d}:59"
        peak_revenue_hour = max(hourly_data.items(), key=lambda x: x[1]["total_revenue"])[0]
        peak_revenue_hour_display = f"{peak_revenue_hour:02d}:00 - {peak_revenue_hour:02d}:59"

        print(f"\nSummary: {total_orders} orders across {total_hours} active hours, ${total_revenue:.2f} total revenue")
        print(f"Peak order hour: {peak_hour_display} ({hourly_data[peak_hour]['order_count']} orders)")
        print(
            f"Peak revenue hour: {peak_revenue_hour_display} (${hourly_data[peak_revenue_hour]['total_revenue']:.2f})")

    def _display_cancel_rate(self, orders, filter_description):
        """Display the cancellation rate for the filtered orders."""
        # Create filter message
        filter_msg = f" (filtered by: {filter_description})" if filter_description else ""

        # Display the header
        print(f"\nCancellation Rate Analysis{filter_msg}")

        if not orders:
            print("No orders match the current filters.")
            return

        # Count total orders and canceled orders
        total_orders = len(orders)
        canceled_orders = sum(1 for order in orders if hasattr(order, 'status') and order.status == "canceled")

        # Calculate cancellation rate
        cancellation_rate = (canceled_orders / total_orders) * 100 if total_orders > 0 else 0

        # Create a simple box display for the results
        print("┌─────────────────────────────────────────────┐")
        print(f"│ Total Orders:      {total_orders:6d}                  │")
        print(f"│ Canceled Orders:   {canceled_orders:6d}                  │")
        print(f"│ Cancellation Rate: {cancellation_rate:6.2f}%                 │")
        print("└─────────────────────────────────────────────┘")

        # Add some contextual analysis based on the rate
        if cancellation_rate == 0:
            print("\nExcellent! No canceled orders in this dataset.")
        elif cancellation_rate < 5:
            print("\nLow cancellation rate. This indicates good operational efficiency.")
        elif cancellation_rate < 10:
            print("\nModerate cancellation rate. Consider reviewing order fulfillment processes.")
        elif cancellation_rate < 15:
            print("\nElevated cancellation rate. This may indicate operational issues that need attention.")
        else:
            print("\nHigh cancellation rate. Immediate review of order handling processes recommended.")

        # Add additional details if specific filters are active
        if "status=" in filter_msg:
            print("\nNote: The '--status' filter may affect the cancellation rate calculation.")