import os
import json
import csv
from datetime import datetime
from orderflow.commands.base import Command
from orderflow.commands.view import ViewCommand


class ExportCommand(Command):
    """Command to export filtered orders to a file with CSV or JSON formats"""

    def __init__(self, storage):
        self.storage = storage
        # Create a ViewCommand instance to reuse its filtering logic
        self.view_command = ViewCommand(storage)

    def add_arguments(self, parser):
        # Output options
        output_group = parser.add_argument_group('Output Options')
        output_group.add_argument(
            '--format',
            choices=['csv', 'json'],
            default='csv',
            help='Output file format (default: csv)'
        )
        output_group.add_argument(
            '--output',
            required=True,
            help='Path to the output file'
        )
        output_group.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite output file if it exists (default: ask for confirmation)'
        )
        output_group.add_argument(
            '--pretty-json',
            action='store_true',
            help='Format JSON output with indentation (default: compact)'
        )

        # Add all the filtering options from ViewCommand
        # We'll reuse those directly to keep filtering consistent

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
            choices=ViewCommand.VALID_STATUSES,
            help=f'Filter orders by status (choices: {", ".join(ViewCommand.VALID_STATUSES)})'
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
            help='Show orders from this date (YYYY-MM-DD format)'
        )
        date_group.add_argument(
            '--to-date',
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

        # Add examples to epilog
        parser.epilog = """
Examples:
  # Export all orders to a CSV file
  orderflow export --output orders.csv

  # Export orders to a JSON file with pretty formatting
  orderflow export --format json --output orders.json --pretty-json

  # Export today's orders only
  orderflow export --today --output todays_orders.csv

  # Export orders with filtering
  orderflow export --status delivered --from-date 2023-07-01 --to-date 2023-07-31 --output monthly_delivered.csv

  # Export orders for a specific customer
  orderflow export --customer "Smith" --output customer_smith.csv

  # Export orders with a specific tag
  orderflow export --tag "delivery" --format json --output delivery_orders.json
"""

    def execute(self, args):
        try:
            # Check if output file exists
            if os.path.exists(args.output) and not args.overwrite:
                confirm = input(f"File '{args.output}' already exists. Overwrite? (y/n): ")
                if confirm.lower() != 'y':
                    print("Export canceled.")
                    return None

            # Get all orders
            all_orders = self.storage.get_orders()

            if not all_orders:
                print("No orders found in the system.")
                return None

            # Use ViewCommand's filtering logic
            filtered_orders = self.view_command._apply_filters(all_orders, args)

            # Sort orders (same as ViewCommand)
            if args.sort_by == 'order_total':
                filtered_orders.sort(key=lambda x: x.order_total, reverse=args.reverse)
            else:  # order_time
                filtered_orders.sort(key=lambda x: x.order_time, reverse=args.reverse)

            if not filtered_orders:
                print("No orders found matching the criteria.")
                return None

            # Export orders based on format
            if args.format == 'csv':
                self._export_csv(filtered_orders, args.output)
            else:  # json
                self._export_json(filtered_orders, args.output, args.pretty_json)

            # Print success message with filter details
            count = len(filtered_orders)

            # Build filter description
            filter_parts = []
            if args.status:
                filter_parts.append(f"status={args.status}")
            if args.active_only:
                filter_parts.append("active-only")
            if args.today:
                filter_parts.append("today")
            if args.from_date:
                filter_parts.append(f"from={args.from_date}")
            if args.to_date:
                filter_parts.append(f"to={args.to_date}")
            if args.dish:
                filter_parts.append(f"dish={args.dish}")
            if args.customer:
                filter_parts.append(f"customer={args.customer}")
            if args.tag:
                filter_parts.append(f"tag={args.tag}")
            if args.with_notes:
                filter_parts.append("with-notes")
            if args.without_notes:
                filter_parts.append("without-notes")

            filter_text = ""
            if filter_parts:
                filter_text = f" (filters: {', '.join(filter_parts)})"

            print(
                f"Successfully exported {count} orders{filter_text} to '{args.output}' in {args.format.upper()} format.")
            return filtered_orders

        except Exception as e:
            print(f"Error exporting orders: {str(e)}")
            return None

    def _export_csv(self, orders, output_path):
        """Export orders to a CSV file with flattened structure"""
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Define CSV columns
            fieldnames = [
                'order_id', 'customer_name', 'dishes', 'order_total',
                'status', 'order_time', 'tags', 'notes'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for order in orders:
                # Format date for readability
                try:
                    dt = datetime.fromisoformat(order.order_time)
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    formatted_time = order.order_time

                # Format dishes with quantities
                dishes_str = order.get_formatted_dishes()

                # Format tags
                tags_str = ", ".join(order.tags) if order.tags else ""

                # Write the row with properly flattened data
                writer.writerow({
                    'order_id': order.order_id,
                    'customer_name': order.customer_name,
                    'dishes': dishes_str,
                    'order_total': order.order_total,
                    'status': order.status,
                    'order_time': formatted_time,
                    'tags': tags_str,
                    'notes': order.notes
                })

    def _export_json(self, orders, output_path, pretty=False):
        """Export orders to a JSON file with full structure preserved"""
        # Convert orders to dictionaries with full structure
        orders_data = []
        for order in orders:
            # Use order's to_dict but with some enhancements for export
            order_dict = order.to_dict()

            # Ensure dishes is an array of objects (not a string)
            if isinstance(order.dishes, list):
                order_dict['dishes'] = order.dishes

            # Parse tags into an array if it's a string
            if isinstance(order_dict['tags'], str) and order_dict['tags']:
                order_dict['tags'] = [t.strip() for t in order_dict['tags'].split(',')]
            elif not order_dict['tags']:
                order_dict['tags'] = []

            orders_data.append(order_dict)

        # Write to file with optional pretty printing
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            if pretty:
                json.dump(orders_data, jsonfile, indent=2, ensure_ascii=False)
            else:
                json.dump(orders_data, jsonfile, ensure_ascii=False)