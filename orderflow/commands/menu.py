import json
import os

from orderflow.commands.base import Command


class MenuCommand(Command):
    """Command class for managing restaurant menus."""

    def __init__(self, storage):
        # In-memory storage for menu items
        self.storage = storage
        self.menu_items = {}

    def add_arguments(self, parser):
        """Add menu-specific command arguments."""
        # Add restaurant flag to the main menu parser
        parser.add_argument('--restaurant', required=True, help='Restaurant ID')

        # Create subparsers for menu subcommands
        subparsers = parser.add_subparsers(dest='menu_action', help='Menu action')

        # Add dish subcommand
        add_parser = subparsers.add_parser('add', help='Add a new dish to the menu')
        add_parser.add_argument('--dish', required=True, help='Name of the dish')
        add_parser.add_argument('--price', required=True, type=float, help='Price of the dish')
        add_parser.add_argument('--category', required=True, help='Category of the dish (e.g., starter, main, dessert)')

        # Remove dish subcommand
        remove_parser = subparsers.add_parser('remove', help='Remove a dish from the menu')
        remove_parser.add_argument('--dish', required=True, help='Name of the dish to remove')

        # Update dish subcommand
        update_parser = subparsers.add_parser('update', help='Update a dish on the menu')
        update_parser.add_argument('--dish', required=True, help='Name of the dish to update')
        update_parser.add_argument('--price', type=float, help='New price of the dish')
        update_parser.add_argument('--category', help='New category of the dish')

        # List menu subcommand
        subparsers.add_parser('list', help='List all dishes on the menu')

    def execute(self, args):
        """Execute the menu command based on subcommand."""
        self.current_restaurant = args.restaurant

        # Check if restaurant exists
        restaurant_dir = os.path.join('data', self.current_restaurant)
        if not os.path.exists(restaurant_dir):
            print(f"Error: Restaurant with ID '{self.current_restaurant}' does not exist.")
            return

        # Load menu from file
        self._load_menu()

        if not hasattr(args, 'menu_action') or args.menu_action is None:
            print("Error: Please specify a menu action (add, remove, update, list)")
            return

        if args.menu_action == 'add':
            self._add_dish(args)
        elif args.menu_action == 'remove':
            self._remove_dish(args)
        elif args.menu_action == 'update':
            self._update_dish(args)
        elif args.menu_action == 'list':
            self._list_menu()

    def _load_menu(self):
        """Load menu from the restaurant's menu file."""
        menu_path = self._get_menu_path()

        # Reset menu items
        self.menu_items = {}

        # If file exists, load menu from it
        if os.path.exists(menu_path):
            try:
                with open(menu_path, 'r') as f:
                    self.menu_items = json.load(f)
            except json.JSONDecodeError:
                print(
                    f"Failed to parse menu data for restaurant '{self.current_restaurant}'. Starting with empty menu.")
            except Exception as e:
                print(
                    f"Failed to load menu for restaurant '{self.current_restaurant}': {str(e)}. Starting with empty menu.")

    def _save_menu(self):
        """Save menu to the restaurant's menu file."""
        menu_path = self._get_menu_path()

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(menu_path), exist_ok=True)

        try:
            with open(menu_path, 'w') as f:
                json.dump(self.menu_items, f, indent=2)
        except Exception as e:
            print(f"Could not save menu to disk: {str(e)}")

    def _get_menu_path(self):
        """Get the path to the menu file for the current restaurant."""
        return os.path.join('data', self.current_restaurant, 'menu.json')

    def _add_dish(self, args):
        """Add a new dish to the menu."""
        dish_name = args.dish

        if dish_name in self.menu_items:
            print(f"Error: Dish '{dish_name}' already exists on the menu.")
            return

        # Add the dish to the menu
        self.menu_items[dish_name] = {
            'price': args.price,
            'category': args.category
        }

        # Save the updated menu
        self._save_menu()

        print(f"Success: Added '{dish_name}' to the menu (Price: ₹{args.price}, Category: {args.category}).")

    def _remove_dish(self, args):
        """Remove a dish from the menu."""
        dish_name = args.dish

        if dish_name not in self.menu_items:
            print(f"Error: Dish '{dish_name}' not found on the menu.")
            return

        # Remove the dish from the menu
        del self.menu_items[dish_name]

        # Save the updated menu
        self._save_menu()

        print(f"Success: Removed '{dish_name}' from the menu.")

    def _update_dish(self, args):
        """Update a dish on the menu."""
        dish_name = args.dish

        if dish_name not in self.menu_items:
            print(f"Error: Dish '{dish_name}' not found on the menu.")
            return

        dish = self.menu_items[dish_name]
        changes_made = False
        change_details = []

        # Update price if specified
        if args.price is not None:
            old_price = dish['price']
            dish['price'] = args.price
            changes_made = True
            change_details.append(f"Price: ₹{old_price} → ₹{args.price}")

        # Update category if specified
        if args.category is not None:
            old_category = dish['category']
            dish['category'] = args.category
            changes_made = True
            change_details.append(f"Category: {old_category} → {args.category}")

        if changes_made:
            # Save the updated menu
            self._save_menu()

            print(f"Success: Updated '{dish_name}' with the following changes:")
            for detail in change_details:
                print(f"  - {detail}")
        else:
            print(f"No changes made to '{dish_name}'.")

    def _list_menu(self):
        """List all dishes on the menu."""
        if not self.menu_items:
            print(f"The menu for restaurant '{self.current_restaurant}' is currently empty.")
            return

        print(f"\nMenu for Restaurant: {self.current_restaurant}")
        print("=" * 60)
        print(f"{'Dish Name':<30} {'Category':<15} {'Price':>10}")
        print("-" * 60)

        # Group dishes by category for organized display
        by_category = {}
        for dish_name, details in self.menu_items.items():
            category = details['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((dish_name, details['price']))

        # Display dishes sorted by category
        for category, dishes in sorted(by_category.items()):
            for dish_name, price in sorted(dishes):
                print(f"{dish_name:<30} {category:<15} ₹{price:>9.2f}")

        print("=" * 60)
        print(f"Total Items: {len(self.menu_items)}")