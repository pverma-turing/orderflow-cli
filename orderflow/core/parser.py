import argparse
from orderflow.commands.add import AddCommand
from orderflow.commands.export import ExportCommand
from orderflow.commands.view import ViewCommand
from orderflow.commands.update_status import UpdateStatusCommand
from orderflow.commands.check_duplicates import CheckDuplicatesCommand


def create_parser(storage):
    """Create and configure the argument parser with detailed help"""
    parser = argparse.ArgumentParser(
        description='OrderFlow - Restaurant Order Tracker CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
OrderFlow is a command-line tool for restaurant order management.
It allows tracking food orders, analyzing sales data, and generating reports.

For detailed help on a specific command, use:
  orderflow <command> --help
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Add command
    add_parser = subparsers.add_parser(
        'add',
        help='Add a new order',
        description='Create a new order in the system with details like customer, dishes, and total.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_command = AddCommand(storage)
    add_command.add_arguments(add_parser)
    add_parser.set_defaults(func=add_command.execute)

    # View command
    view_parser = subparsers.add_parser(
        'view',
        help='View and analyze orders',
        description='View orders with powerful filtering, sorting, and reporting options.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    view_command = ViewCommand(storage)
    view_command.add_arguments(view_parser)
    view_parser.set_defaults(func=view_command.execute)

    # Update status command
    update_status_parser = subparsers.add_parser(
        'update-status',
        help='Update an order status',
        description='Change the status of an existing order (new, preparing, delivered, canceled).',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    update_status_command = UpdateStatusCommand(storage)
    update_status_command.add_arguments(update_status_parser)
    update_status_parser.set_defaults(func=update_status_command.execute)

    # New: Check duplicates command
    check_duplicates_parser = subparsers.add_parser(
        'check-duplicates',
        help='Identify potential duplicate orders',
        description='Find duplicate orders based on customer, dishes, and time proximity.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    check_duplicates_command = CheckDuplicatesCommand(storage)
    check_duplicates_command.add_arguments(check_duplicates_parser)
    check_duplicates_parser.set_defaults(func=check_duplicates_command.execute)

    # Export command
    export_parser = subparsers.add_parser(
        'export',
        help='Export orders to CSV or JSON file',
        description='Export filtered orders to a file in CSV or JSON format.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    export_command = ExportCommand(storage)
    export_command.add_arguments(export_parser)
    export_parser.set_defaults(func=export_command.execute)

    return parser