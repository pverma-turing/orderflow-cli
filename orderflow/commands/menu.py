import json
import os

from orderflow.commands.base import Command


class MenuCommand(Command):
    """Command class for managing restaurant menus."""

    # Define valid categories
    VALID_CATEGORIES = {'starter', 'main', 'dessert', 'beverage'}

    def __init__(self, storage):
        # In-memory storage for menu items
        self.current_restaurant = None
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
        add_parser.add_argument(
            '--category',
            required=True,
            help=f'Category of the dish (allowed values: {", ".join(self.VALID_CATEGORIES)})'
        )

        # Remove dish subcommand
        remove_parser = subparsers.add_parser('remove', help='Remove a dish from the menu')
        remove_parser.add_argument('--dish', required=True, help='Name of the dish to remove')

        # Update dish subcommand
        update_parser = subparsers.add_parser('update', help='Update a dish on the menu')
        update_parser.add_argument('--dish', required=True, help='Name of the dish to update')
        update_parser.add_argument('--price', type=float, help='New price of the dish')
        update_parser.add_argument(
            '--category',
            help=f'New category of the dish (allowed values: {", ".join(self.VALID_CATEGORIES)})'
        )

        # List menu subcommand
        list_parser = subparsers.add_parser('list', help='List all dishes on the menu')
        list_parser.add_argument('--json', action='store_true', help='Output menu as JSON')

        # Search menu subcommand
        search_parser = subparsers.add_parser('search', help='Search for dishes in the menu')
        search_parser.add_argument(
            '--query',
            help='Search string for dish names (optional - if not provided, all dishes are listed)'
        )
        search_parser.add_argument(
            '--category',
            help=f'Filter by category (allowed values: {", ".join(self.VALID_CATEGORIES)})'
        )
        search_parser.add_argument(
            '--limit',
            type=int,
            help='Maximum number of results to display'
        )
        search_parser.add_argument(
            '--json',
            action='store_true',
            help='Output search results as JSON'
        )

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
            print("Error: Please specify a menu action (add, remove, update, list, search)")
            return

        if args.menu_action == 'add':
            self._add_dish(args)
        elif args.menu_action == 'remove':
            self._remove_dish(args)
        elif args.menu_action == 'update':
            self._update_dish(args)
        elif args.menu_action == 'list':
            self._list_menu(args)
        elif args.menu_action == 'search':
            self._search_menu(args)

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

    def _validate_dish_name(self, dish_name):
        """Validate that a dish name is non-empty after trimming whitespace."""
        if not dish_name or not dish_name.strip():
            return False
        return True

    def _validate_price(self, price):
        """Validate that a price is a positive number."""
        return price is not None and price > 0

    def _validate_category(self, category):
        """Validate that a category is in the list of valid categories."""
        return category in self.VALID_CATEGORIES

    def _add_dish(self, args):
        """Add a new dish to the menu."""
        dish_name = args.dish

        # Validate dish name
        if not self._validate_dish_name(dish_name):
            print("Error: Dish name cannot be empty.")
            return

        # Validate price
        if not self._validate_price(args.price):
            print("Error: Price must be a positive number.")
            return

        # Validate category
        if not self._validate_category(args.category):
            print(f"Error: Invalid category '{args.category}'. Allowed values: {', '.join(self.VALID_CATEGORIES)}")
            return

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
            # Validate price
            if not self._validate_price(args.price):
                print("Error: Price must be a positive number.")
                return

            old_price = dish['price']
            dish['price'] = args.price
            changes_made = True
            change_details.append(f"Price: ₹{old_price} → ₹{args.price}")

        # Update category if specified
        if args.category is not None:
            # Validate category
            if not self._validate_category(args.category):
                print(f"Error: Invalid category '{args.category}'. Allowed values: {', '.join(self.VALID_CATEGORIES)}")
                return

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

    def _list_menu(self, args):
        """List all dishes on the menu."""
        # Check if JSON output is requested
        if hasattr(args, 'json') and args.json:
            # Output as raw JSON
            print(json.dumps(self.menu_items) if self.menu_items else "{}")
            return

        # Standard formatted output
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

    def _search_menu(self, args):
        """Search for dishes in the menu by name (optionally) and other filters."""
        # Get the query if provided, or None if not
        query = args.query.lower() if hasattr(args, 'query') and args.query else None
        category_filter = args.category.lower() if hasattr(args, 'category') and args.category else None
        limit = args.limit if hasattr(args, 'limit') and args.limit is not None else None
        use_json = hasattr(args, 'json') and args.json

        # Validate limit if provided
        if limit is not None and limit <= 0:
            print("Error: Limit must be a positive integer.")
            return

        # Validate category if provided
        if category_filter and category_filter.lower() not in [c.lower() for c in self.VALID_CATEGORIES]:
            print(f"Error: Invalid category '{args.category}'. Allowed values: {', '.join(self.VALID_CATEGORIES)}")
            return

        matching_dishes = {}

        # Find matching dishes based on filters
        for dish_name, details in self.menu_items.items():
            # If query is provided, check if dish name contains it (case-insensitive)
            if query and query not in dish_name.lower():
                continue

            # If category filter is provided, check category as well (case-insensitive)
            if category_filter and details['category'].lower() != category_filter:
                continue

            # Dish passed all filters, add to matches
            matching_dishes[dish_name] = details

        # No matching dishes found
        if not matching_dishes:
            if use_json:
                print("{}")
            else:
                print("No matching dishes found.")
            return

        # Apply limit to the matching dishes if needed
        if limit is not None and limit < len(matching_dishes):
            # For JSON output with limit, we need to slice the dictionary
            limited_dishes = {}
            count = 0
            for dish_name, details in sorted(matching_dishes.items()):
                if count >= limit:
                    break
                limited_dishes[dish_name] = details
                count += 1
            matching_dishes = limited_dishes

        # JSON output mode
        if use_json:
            print(json.dumps(matching_dishes))
            return

        # Standard formatted output from here
        # Build search description for header
        if query:
            search_desc = f"'{query}'"
            if category_filter:
                # Find the correctly cased category from the valid list
                correct_case_category = next((c for c in self.VALID_CATEGORIES if c.lower() == category_filter),
                                             args.category)
                search_desc += f" in category '{correct_case_category}'"
            header_text = f"Search Results for {search_desc} in Restaurant: {self.current_restaurant}"
        else:
            # No query - this is a menu listing (possibly filtered by category)
            if category_filter:
                # Find the correctly cased category from the valid list
                correct_case_category = next((c for c in self.VALID_CATEGORIES if c.lower() == category_filter),
                                             args.category)
                header_text = f"Menu Items in Category '{correct_case_category}' for Restaurant: {self.current_restaurant}"
            else:
                header_text = f"Menu for Restaurant: {self.current_restaurant}"

        # Display matching dishes
        print(f"\n{header_text}")
        print("=" * 60)
        print(f"{'Dish Name':<30} {'Category':<15} {'Price':>10}")
        print("-" * 60)

        # Group dishes by category for organized display
        by_category = {}
        for dish_name, details in matching_dishes.items():
            category = details['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((dish_name, details['price']))

        # Display dishes sorted by category with limit
        displayed_count = 0

        for category, dishes in sorted(by_category.items()):
            for dish_name, price in sorted(dishes):
                # For text output, limit is handled here during display
                if limit is not None and displayed_count >= limit:
                    break

                print(f"{dish_name:<30} {category:<15} ₹{price:>9.2f}")
                displayed_count += 1

            # If we've reached the limit, break out of the category loop as well
            if limit is not None and displayed_count >= limit:
                break

        print("=" * 60)

        # Show result count, noting if limited
        if limit is not None and len(matching_dishes) > displayed_count:
            print(f"Found {len(matching_dishes)} matching dishes (showing first {limit})")
        else:
            print(f"Found {len(matching_dishes)} matching dishes")