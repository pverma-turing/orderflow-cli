import sys

from orderflow.config.config_utils import get_active_restaurant_id
from orderflow.storage.json_storage import JsonStorage
from orderflow.core.parser import create_parser


def main():
    """Main entry point for the application"""
    # Initialize storage
    restaurant_id = get_active_restaurant_id()
    storage = JsonStorage(restaurant_id)

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