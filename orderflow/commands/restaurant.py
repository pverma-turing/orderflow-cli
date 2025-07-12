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

    # Valid fields for sorting
    VALID_SORT_FIELDS = ['name', 'location', 'cuisine']

    def add_arguments(self, parser):
        """Add restaurant command arguments."""
        restaurant_subparsers = parser.add_subparsers(dest='action', help='Restaurant action to perform')

        # Register subcommand remains the same
        register_parser = restaurant_subparsers.add_parser('register', help='Register a new restaurant')
        register_parser.add_argument('--id', required=True, help='Unique restaurant ID')
        register_parser.add_argument('--name', required=True, help='Restaurant name')
        register_parser.add_argument('--cuisine', help='Type of cuisine')
        register_parser.add_argument('--location', help='Restaurant location')
        register_parser.add_argument('--contact', help='Contact information')

        # List subcommand - updated with sort-by option
        list_parser = restaurant_subparsers.add_parser('list', help='List all registered restaurants')
        list_parser.add_argument('--search', help='Filter restaurants by name (case-insensitive)')
        list_parser.add_argument('--cuisine', help='Filter restaurants by cuisine (case-insensitive)')
        list_parser.add_argument('--sort-by', help='Sort results by field (name, location, cuisine)')

        # Other subparsers remain the same
        use_parser = restaurant_subparsers.add_parser('use', help='Set the active restaurant context')
        use_parser.add_argument('--id', required=True, help='Restaurant ID to use')

        show_parser = restaurant_subparsers.add_parser('show', help='Show details of a specific restaurant')
        show_parser.add_argument('--id', required=True, help='Restaurant ID to show')

        edit_parser = restaurant_subparsers.add_parser('edit', help='Edit a restaurant\'s details')
        edit_parser.add_argument('--id', required=True, help='Restaurant ID to edit')
        edit_parser.add_argument('--name', help='New restaurant name')
        edit_parser.add_argument('--cuisine', help='New cuisine type')
        edit_parser.add_argument('--location', help='New restaurant location')
        edit_parser.add_argument('--contact', help='New contact information')

    def execute(self, args):
        """Execute the restaurant command based on the action."""
        if not hasattr(args, 'action') or not args.action:
            print("Error: Please specify an action (register, list, use, show, or edit)")
            return False

        if args.action == 'register':
            return self.register_restaurant(args)
        elif args.action == 'list':
            return self.list_restaurants(args)
        elif args.action == 'use':
            return self.use_restaurant(args)
        elif args.action == 'show':
            return self.show_restaurant(args)
        elif args.action == 'edit':
            return self.edit_restaurant(args)
        else:
            print(f"Error: Unknown action '{args.action}'")
            return False

    def edit_restaurant(self, args):
        """Edit details of an existing restaurant.

        Args:
            args: Command arguments with restaurant ID and fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        restaurant_id = args.id

        # Get the current restaurant data
        restaurant_data = self._get_restaurant_by_id(restaurant_id)
        if not restaurant_data:
            print(f"[Error] Restaurant with ID '{restaurant_id}' not found.")
            return False

        # Create Restaurant model from existing data
        restaurant = Restaurant.from_dict(restaurant_data)

        # Track whether any fields were updated
        updated = False

        # Update only fields that are explicitly provided
        if hasattr(args, 'name') and args.name is not None:
            restaurant.name = args.name
            updated = True

        if hasattr(args, 'cuisine') and args.cuisine is not None:
            restaurant.cuisine = args.cuisine
            updated = True

        if hasattr(args, 'location') and args.location is not None:
            restaurant.location = args.location
            updated = True

        if hasattr(args, 'contact') and args.contact is not None:
            restaurant.contact = args.contact
            updated = True

        # If no fields were updated, inform the user
        if not updated:
            print("No fields were provided for update. Restaurant remains unchanged.")
            return True

        # Update the restaurant in the registry
        if self._update_restaurant_in_registry(restaurant):
            print(f"[Success] Updated restaurant: {restaurant_id}")
            return True
        else:
            print(f"Error: Failed to update restaurant '{restaurant_id}'")
            return False

    def _update_restaurant_in_registry(self, restaurant):
        """Update a restaurant in the registry.

        Args:
            restaurant (Restaurant): Restaurant model to update

        Returns:
            bool: True if successful, False otherwise
        """
        restaurants_file = Path("data/restaurants.json")

        if not restaurants_file.exists():
            return False

        try:
            # Read the current registry
            with open(restaurants_file, 'r') as f:
                restaurants = json.load(f)

            # Find the restaurant to update
            found = False
            for i, rest in enumerate(restaurants):
                if rest.get('id') == restaurant.id:
                    # Update the restaurant with new data
                    restaurants[i] = restaurant.to_dict()
                    found = True
                    break

            if not found:
                return False

            # Write back to the registry
            with open(restaurants_file, 'w') as f:
                json.dump(restaurants, f, indent=2)

            return True

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error accessing restaurant registry: {e}")
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
        # Check if restaurant ID already exists
        if self._restaurant_exists(args.id):
            print(f"[Error] Restaurant with ID '{args.id}' already exists.")
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

    def _restaurant_exists(self, restaurant_id):
        """Check if a restaurant with the given ID already exists.

        Args:
            restaurant_id (str): Restaurant ID to check

        Returns:
            bool: True if restaurant exists, False otherwise
        """
        restaurants_file = Path("data/restaurants.json")

        # If restaurants.json doesn't exist, no restaurants exist
        if not restaurants_file.exists():
            return False

        try:
            with open(restaurants_file, 'r') as f:
                restaurants = json.load(f)

            # Check if any restaurant has the given ID
            return any(restaurant.get('id') == restaurant_id for restaurant in restaurants)
        except (json.JSONDecodeError, IOError):
            # If there's an error reading the file, assume no restaurants exist
            # (We'll create a new file when registering)
            return False

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
        return self._restaurant_exists(restaurant_id)

    def list_restaurants(self, args=None):
        """List all restaurants, optionally filtered and sorted.

        Args:
            args: Command arguments, may include search, cuisine, and sort-by parameters

        Returns:
            bool: True if successful, False otherwise
        """
        restaurants = self._load_restaurants()

        if not restaurants:
            print("No restaurants registered yet.")
            return True

        # Track which filters are applied for appropriate messaging
        search_applied = args and hasattr(args, 'search') and args.search
        cuisine_applied = args and hasattr(args, 'cuisine') and args.cuisine

        # Apply search filter if specified
        filtered_restaurants = restaurants
        if search_applied:
            search_keyword = args.search.lower()
            filtered_restaurants = [
                r for r in filtered_restaurants
                if search_keyword in r.get('name', '').lower()
            ]

            # If no results after search filter and no cuisine filter applied yet
            if not filtered_restaurants and not cuisine_applied:
                print(f"[Info] No restaurants found matching '{args.search}'")
                return True

        # Apply cuisine filter if specified
        if cuisine_applied:
            cuisine_name = args.cuisine.lower()
            filtered_restaurants = [
                r for r in filtered_restaurants
                if r.get('cuisine', '').lower() == cuisine_name
            ]

            # If no results after cuisine filter
            if not filtered_restaurants:
                if search_applied:
                    # Both filters were applied
                    print(f"[Info] No restaurants found matching '{args.search}' with cuisine '{args.cuisine}'")
                else:
                    # Only cuisine filter was applied
                    print(f"[Info] No restaurants found for cuisine '{args.cuisine}'")
                return True

        # Apply sorting if specified
        sort_applied = args and hasattr(args, 'sort_by') and args.sort_by
        if sort_applied:
            sort_field = args.sort_by.lower()

            # Validate sort field
            if sort_field not in self.VALID_SORT_FIELDS:
                print(
                    f"[Error] Unsupported sort field '{sort_field}'. Allowed values: {', '.join(self.VALID_SORT_FIELDS)}")
                return False

            # Sort the filtered results
            filtered_restaurants = sorted(
                filtered_restaurants,
                key=lambda r: r.get(sort_field, '').lower()  # Case-insensitive sort
            )

        # Prepare table data
        table_data = []
        for restaurant in filtered_restaurants:
            # Convert to Restaurant model to ensure consistent data access
            r = Restaurant.from_dict(restaurant)
            table_data.append([
                r.id,
                r.name,
                r.cuisine or '',  # Handle None values
                r.location or ''
            ])

        # Display table with the results
        headers = ['ID', 'Name', 'Cuisine', 'Location']
        print(tabulate(table_data, headers=headers, tablefmt='pretty'))

        return True

    def _load_restaurants(self):
        """Load restaurants from restaurants.json.

        Returns:
            list: List of restaurant dictionaries, or empty list if none found
        """
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

    def _validate_unique_id(self, restaurant_id):
        """Check if the restaurant ID is unique."""
        restaurants = self._load_restaurants()
        for restaurant in restaurants:
            if restaurant['id'] == restaurant_id:
                return False
        return True

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