from orderflow.commands.base import Command


class MenuCommand(Command):
    """Command class for managing restaurant menus."""

    def __init__(self, storage):
        # In-memory storage for menu items
        self.storage = storage
        self.menu_items = {}

    def add_arguments(self, parser):
        """Add menu-specific command arguments."""
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

        print(f"Success: Added '{dish_name}' to the menu (Price: ₹{args.price}, Category: {args.category}).")

    def _remove_dish(self, args):
        """Remove a dish from the menu."""
        dish_name = args.dish

        if dish_name not in self.menu_items:
            print(f"Error: Dish '{dish_name}' not found on the menu.")
            return

        # Remove the dish from the menu
        del self.menu_items[dish_name]

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
            print(f"Success: Updated '{dish_name}' with the following changes:")
            for detail in change_details:
                print(f"  - {detail}")
        else:
            print(f"No changes made to '{dish_name}'.")

    def _list_menu(self):
        """List all dishes on the menu."""
        if not self.menu_items:
            print("The menu is currently empty.")
            return

        print("\nCurrent Menu:")
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