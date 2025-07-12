import os
import json
from pathlib import Path
from tabulate import tabulate

from orderflow.commands.base import Command


class RestaurantCommand(Command):
    """Command to manage restaurants in the OrderFlow system."""

    def __init__(self, storage):
        self.storage = storage

    def add_arguments(self, parser):
        """Add restaurant command arguments."""
        restaurant_subparsers = parser.add_subparsers(dest='action', help='Restaurant action to perform')

        # Register subcommand
        register_parser = restaurant_subparsers.add_parser('register', help='Register a new restaurant')
        register_parser.add_argument('--id', required=True, help='Unique restaurant ID')
        register_parser.add_argument('--name', required=True, help='Restaurant name')
        register_parser.add_argument('--location', help='Restaurant location')

        # List subcommand
        restaurant_subparsers.add_parser('list', help='List all registered restaurants')

    def execute(self, args):
        """Execute the restaurant command based on the action."""
        if not hasattr(args, 'action') or not args.action:
            print("Error: Please specify an action (register or list)")
            return False

        if args.action == 'register':
            return self.register_restaurant(args)
        elif args.action == 'list':
            return self.list_restaurants()
        else:
            print(f"Error: Unknown action '{args.action}'")
            return False

    def register_restaurant(self, args):
        """Register a new restaurant."""
        # Ensure the restaurant ID is unique
        if not self._validate_unique_id(args.id):
            print(f"Error: Restaurant with ID '{args.id}' already exists")
            return False

        # Create restaurant entry
        restaurant = {
            'id': args.id,
            'name': args.name,
            'location': args.location or ''
        }

        # Add to restaurants.json
        if not self._add_to_restaurants_json(restaurant):
            return False

        # Create restaurant data folder and orders.json file
        if not self._create_restaurant_data_structure(args.id):
            return False

        print(f"Successfully registered restaurant: {args.name} (ID: {args.id})")
        return True

    def list_restaurants(self):
        """List all registered restaurants."""
        restaurants = self._load_restaurants()
        if not restaurants:
            print("No restaurants registered yet.")
            return True

        # Prepare table data
        table_data = [[r['id'], r['name'], r['location']] for r in restaurants]
        headers = ['ID', 'Name', 'Location']

        # Print table using tabulate
        print(tabulate(table_data, headers=headers, tablefmt='pretty'))
        return True

    def _validate_unique_id(self, restaurant_id):
        """Check if the restaurant ID is unique."""
        restaurants = self._load_restaurants()
        for restaurant in restaurants:
            if restaurant['id'] == restaurant_id:
                return False
        return True

    def _load_restaurants(self):
        """Load restaurants from restaurants.json."""
        restaurants_file = Path('data/restaurants.json')
        if not restaurants_file.exists():
            return []

        try:
            with open(restaurants_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error: Invalid JSON in restaurants file")
            return []
        except Exception as e:
            print(f"Error loading restaurants: {e}")
            return []

    def _add_to_restaurants_json(self, restaurant):
        """Add a new restaurant to restaurants.json."""
        restaurants_file = Path('data/restaurants.json')
        restaurants_file.parent.mkdir(exist_ok=True)

        # Load existing restaurants or create new list
        restaurants = self._load_restaurants()
        restaurants.append(restaurant)

        # Write back to file
        try:
            with open(restaurants_file, 'w') as f:
                json.dump(restaurants, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving restaurant data: {e}")
            return False

    def _create_restaurant_data_structure(self, restaurant_id):
        """Create the restaurant data folder and orders.json file."""
        # Create restaurant data folder
        restaurant_folder = Path(f'data/{restaurant_id}')
        try:
            restaurant_folder.mkdir(exist_ok=True)

            # Create empty orders.json file
            orders_file = restaurant_folder / 'orders.json'
            with open(orders_file, 'w') as f:
                json.dump([], f)

            return True
        except Exception as e:
            print(f"Error creating restaurant data structure: {e}")
            return False