import argparse
from orderflow.commands.add import AddCommand
from orderflow.commands.view import ViewCommand


def create_parser(storage):
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        description='OrderFlow - Restaurant Order Tracker CLI'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new order')
    add_command = AddCommand(storage)
    add_command.add_arguments(add_parser)
    add_parser.set_defaults(func=add_command.execute)

    # View command
    view_parser = subparsers.add_parser('view', help='View all orders')
    view_command = ViewCommand(storage)
    view_command.add_arguments(view_parser)
    view_parser.set_defaults(func=view_command.execute)

    return parser