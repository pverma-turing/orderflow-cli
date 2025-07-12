import os
import json
from pathlib import Path
from tabulate import tabulate

from orderflow.commands.base import Command
from orderflow.models.restaurant import Restaurant


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
        register_parser.add_argument('--cuisine', help='Type of cuisine')  # Added cuisine field
        register_parser.add_argument('--location', help='Restaurant location')
        register_parser.add_argument('--contact', help='Contact information')  # Added contact field

        # List subcommand
        restaurant_subparsers.add_parser('list', help='List all registered restaurants')

        # Use subcommand
        use_parser = restaurant_subparsers.add_parser('use', help='Set the active restaurant context')
        use_parser.add_argument('--id', required=True, help='Restaurant ID to use')

        # Show subcommand (new)
        show_parser = restaurant_subparsers.add_parser('show', help='Show details of a specific restaurant')
        show_parser.add_argument('--id', required=True, help='Restaurant ID to show')

    def execute(self, args):
        """Execute the restaurant command based on the action."""
        if not hasattr(args, 'action') or not args.action:
            print("Error: Please specify an action (register, list, use, or show)")
            return False

        if args.action == 'register':
            return self.register_restaurant(args)
        elif args.action == 'list':
            return self.list_restaurants()
        elif args.action == 'use':
            return self.use_restaurant(args)
        elif args.action == 'show':
            return self.show_restaurant(args)
        else:
            print(f"Error: Unknown action '{args.action}'")
            return False

    def show_restaurant(self, args):
        """Show details of a specific restaurant.

        Args:
            args: Command arguments with restaurant ID

        Returns:
            bool: True if successful, False otherwise
        """
        restaurant_id = args.id
        restaurant = self._get_restaurant_by_id(restaurant_id)

        if not restaurant:
            print(f"[Error] Restaurant with ID '{restaurant_id}' not found.")
            return False

        # Convert dict to Restaurant model
        restaurant_model = Restaurant.from_dict(restaurant)

        # Print restaurant details in aligned format
        print(f"ID       : {restaurant_model.id}")
        print(f"Name     : {restaurant_model.name}")

        if restaurant_model.cuisine:
            print(f"Cuisine  : {restaurant_model.cuisine}")

        if restaurant_model.location:
            print(f"Location : {restaurant_model.location}")

        if restaurant_model.contact:
            print(f"Contact  : {restaurant_model.contact}")

        return True

    def _get_restaurant_by_id(self, restaurant_id):
        """Get a restaurant by ID from the registry.

        Args:
            restaurant_id (str): ID of the restaurant to find

        Returns:
            dict: Restaurant data or None if not found
        """
        restaurants_file = Path("data/restaurants.json")

        if not restaurants_file.exists():
            return None

        try:
            with open(restaurants_file, 'r') as f:
                restaurants = json.load(f)

            # Find restaurant with matching ID
            for restaurant in restaurants:
                if restaurant.get('id') == restaurant_id:
                    return restaurant

            return None
        except (json.JSONDecodeError, IOError):
            return None

    def register_restaurant(self, args):
        """Register a new restaurant."""
        # Ensure the restaurant ID is unique
        if not self._validate_unique_id(args.id):
            print(f"Error: Restaurant with ID '{args.id}' already exists")
            return False

        # Create restaurant model and convert to dict
        restaurant = Restaurant(
            id=args.id,
            name=args.name,
            cuisine=args.cuisine if hasattr(args, 'cuisine') else None,
            location=args.location if hasattr(args, 'location') else None,
            contact=args.contact if hasattr(args, 'contact') else None
        )

        restaurant_dict = restaurant.to_dict()

        # Add to restaurants.json
        if not self._add_to_restaurants_json(restaurant_dict):
            return False

        # Create restaurant data folder and orders.json file
        if not self._create_restaurant_data_structure(args.id):
            return False

        print(f"Successfully registered restaurant: {args.name} (ID: {args.id})")
        return True

    def use_restaurant(self, args):
        """Set the active restaurant context.

        Args:
            args: Command arguments with restaurant ID

        Returns:
            bool: True if successful, False otherwise
        """
        restaurant_id = args.id

        # Validate restaurant exists
        if not self._validate_restaurant_exists(restaurant_id):
            print(f"Error: Restaurant ID '{restaurant_id}' not found in restaurants.json")
            return False

        # Save to config file
        config_path = Path('.orderflowrc')
        config = {}

        try:
            # Try to load existing config if it exists
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # If there's an error loading the file, create a new config
            print(f"Notice: Creating new configuration file (.orderflowrc)")
            config = {}

        # Update the active restaurant
        config['active_restaurant'] = restaurant_id

        try:
            # Save the updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"Now using restaurant: {restaurant_id}")
            return True
        except IOError as e:
            print(f"Error saving configuration: {e}")
            return False

    def _validate_restaurant_exists(self, restaurant_id):
        """Check if the restaurant ID exists in the central registry.

        Args:
            restaurant_id (str): ID to validate

        Returns:
            bool: True if restaurant exists, False otherwise
        """
        restaurants_file = Path("data/restaurants.json")

        # If the registry doesn't exist, restaurant can't exist
        if not restaurants_file.exists():
            return False

        try:
            with open(restaurants_file, 'r') as f:
                restaurants = json.load(f)

            # Check if any restaurant has the matching ID
            return any(restaurant['id'] == restaurant_id for restaurant in restaurants)
        except (json.JSONDecodeError, IOError, KeyError):
            # If there's any error reading the file or accessing data, assume restaurant doesn't exist
            return False

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