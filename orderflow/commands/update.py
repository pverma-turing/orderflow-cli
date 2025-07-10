"""
Command to update non-status fields of an order.
"""

import argparse
from typing import List


def setup_parser(subparsers):
    """Configure the argument parser for the 'update' command."""
    parser = subparsers.add_parser(
        'update',
        help='Update non-status fields of an existing order'
    )

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

    parser.set_defaults(func=handle_command)


def handle_command(args):
    """Handle the update command execution."""
    # Validate that at least one update field was provided
    update_fields = [
        args.customer_name is not None,
        args.total is not None,
        len(args.add_tag) > 0,
        len(args.remove_tag) > 0,
        args.note is not None
    ]

    if not any(update_fields):
        print("Error: At least one field must be provided to update")
        return 1

    # Just print a confirmation message for now
    print(f"Ready to update order {args.id}")

    return 0