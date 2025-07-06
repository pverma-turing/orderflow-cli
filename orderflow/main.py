import sys
from orderflow.storage.json_storage import JsonStorage
from orderflow.core.parser import create_parser


def main():
    """Main entry point for the application"""
    # Initialize storage
    storage = JsonStorage()

    # Create parser
    parser = create_parser(storage)

    # Parse arguments
    args = parser.parse_args()

    # Execute command if provided
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()