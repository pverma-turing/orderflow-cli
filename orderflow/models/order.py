import uuid
import re
from datetime import datetime

from orderflow.models.delivery_info import DeliveryInfo


class Order:
    """Represents a food order in the system with dish quantities"""

    VALID_STATUSES = ["new", "preparing", "delivered", "canceled"]
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, customer_name, dishes, order_total, status="new",
                 order_id=None, order_time=None, tags=None, notes=None, status_history=None,
                 delivery_info=None, assignment_history=None):
        # Validate customer name
        if not customer_name or not customer_name.strip():
            raise ValueError("Customer name cannot be empty")
        self.customer_name = customer_name.strip()

        self.delivery_info = delivery_info
        self.assignment_history = assignment_history or []

        # Process dishes (now supporting quantities)
        self.dishes = self._parse_dishes(dishes)
        if not self.dishes:
            raise ValueError("At least one dish must be provided")

        # Validate order total
        try:
            order_total_float = float(order_total)
            if order_total_float <= 0:
                raise ValueError("Order total must be a positive number")
            self.order_total = order_total_float
        except (ValueError, TypeError):
            raise ValueError(f"Invalid order total: {order_total}. Must be a positive number.")

        # Validate status
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {status}. Must be one of: {', '.join(self.VALID_STATUSES)}"
            )
        self.status = status

        # Set or generate order ID
        if order_id:
            # Validate UUID format if provided
            try:
                uuid_obj = uuid.UUID(order_id)
                self.order_id = str(uuid_obj)
            except ValueError:
                raise ValueError(f"Invalid order ID format: {order_id}")
        else:
            self.order_id = str(uuid.uuid4())

        # Handle order time
        if order_time:
            # Validate and normalize timestamp format
            try:
                # Try parsing as ISO 8601
                dt = datetime.fromisoformat(order_time)
                self.order_time = dt.isoformat()
            except ValueError:
                # If that fails, try a more lenient approach
                try:
                    # Try common date-time formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                        try:
                            dt = datetime.strptime(order_time, fmt)
                            self.order_time = dt.isoformat()
                            break
                        except ValueError:
                            continue
                    else:  # If all formats fail
                        raise ValueError(f"Invalid timestamp format: {order_time}")
                except Exception:
                    raise ValueError(f"Invalid timestamp format: {order_time}")
        else:
            # Store current time in ISO format for easy sorting and parsing
            self.order_time = datetime.now().isoformat()

        # Handle tags
        self.tags = []
        if tags:
            if isinstance(tags, list):
                self.tags = [tag.strip() for tag in tags if tag.strip()]
            else:
                # Parse comma-separated tags and strip whitespace
                self.tags = [tag.strip() for tag in tags.split(',') if tag.strip()]

        # Handle notes (allow empty notes)
        self.notes = notes or ""
        if status_history is None:
            self.status_history = [(self.order_time, self.status, None)]
        else:
            # Handle backward compatibility with old format (timestamp, status)
            self.status_history = []
            for entry in status_history:
                if len(entry) == 2:  # Old format without note
                    self.status_history.append((entry[0], entry[1], None))
                else:
                    self.status_history.append(entry)  # New for

    def _parse_dishes(self, dishes):
        """
        Parse dishes input, supporting both:
        1. List of dish dicts with name and quantity (new format)
        2. List of dish names (old format)
        3. String in format "Dish1:2, Dish2:1" (new CLI format)
        4. String in format "Dish1, Dish2" (old CLI format)

        Returns a list of dictionaries: [{"name": "Dish1", "quantity": 2}, ...]
        """
        if not dishes:
            return []

        # 1. Already a list of dish dicts (likely from storage)
        if isinstance(dishes, list) and len(dishes) > 0 and isinstance(dishes[0], dict):
            # Validate each dict has required fields
            result = []
            for dish in dishes:
                if 'name' in dish:
                    # Ensure quantity is an integer >= 1
                    qty = dish.get('quantity', 1)
                    try:
                        qty = int(qty)
                        if qty < 1:
                            qty = 1
                    except (ValueError, TypeError):
                        qty = 1

                    result.append({
                        'name': dish['name'].strip(),
                        'quantity': qty
                    })
            return result

        # 2. List of dish names (old format - convert to new format)
        if isinstance(dishes, list):
            return [{'name': dish.strip(), 'quantity': 1} for dish in dishes if dish.strip()]

        # 3 & 4. String input from CLI - could be either format
        if isinstance(dishes, str):
            result = []
            # Split by commas
            items = [item.strip() for item in dishes.split(',') if item.strip()]

            for item in items:
                # Check if it has quantity indicator (:)
                if ':' in item:
                    # New format: "Dish:Quantity"
                    parts = item.split(':', 1)
                    dish_name = parts[0].strip()
                    if not dish_name:
                        continue

                    try:
                        quantity = int(parts[1].strip())
                        if quantity < 1:
                            quantity = 1
                    except (ValueError, IndexError):
                        quantity = 1

                    result.append({
                        'name': dish_name,
                        'quantity': quantity
                    })
                else:
                    # Old format: just the dish name
                    result.append({
                        'name': item.strip(),
                        'quantity': 1
                    })

            return result

        # Fallback for unexpected input type
        return []

    def get_dish_names(self):
        """Get a simple list of dish names (backward compatible)"""
        return [dish['name'] for dish in self.dishes]

    def get_formatted_dishes(self):
        """Get a formatted string representation of dishes with quantities"""
        return ", ".join([f"{dish['name']} (×{dish['quantity']})" for dish in self.dishes])

    def has_dish(self, dish_name):
        """Check if an order contains a specific dish (case insensitive partial match)"""
        search = dish_name.lower()
        for dish in self.dishes:
            if search in dish['name'].lower():
                return True
        return False

    def get_total_quantity(self):
        """Get the total quantity of all dishes"""
        return sum(dish['quantity'] for dish in self.dishes)

    def calculate_dish_revenue(self):
        """Calculate the revenue for each dish proportionally based on quantity"""
        total_quantity = self.get_total_quantity()
        if total_quantity == 0:  # Defensive programming
            return {}

        # Distribute revenue proportionally
        per_unit_revenue = self.order_total / total_quantity
        return {
            dish['name']: dish['quantity'] * per_unit_revenue
            for dish in self.dishes
        }

    def to_dict(self):
        """Convert order to dictionary for storage"""
        return {
            'order_id': self.order_id,
            'customer_name': self.customer_name,
            'dishes': self.dishes,  # Now a list of dicts with name and quantity
            'order_total': self.order_total,
            'status': self.status,
            'order_time': self.order_time,
            'tags': ','.join(self.tags) if self.tags else "",
            'notes': self.notes,
            'status_history': self.status_history,
            'delivery_info': self.delivery_info.to_dict() if self.delivery_info else {},
            'assignment_history': self.assignment_history
        }

    @classmethod
    def from_dict(cls, data):
        """Create order instance from dictionary data with backward compatibility"""
        # Check required fields
        required_fields = ['order_id', 'customer_name', 'order_total', 'status']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Handle dishes - supporting both old and new formats
        dishes = None

        # New format: dishes is a list of dicts with name and quantity
        if 'dishes' in data and isinstance(data['dishes'], list):
            dishes = data['dishes']
        # Old format: dish_names is a comma-separated string
        elif 'dish_names' in data:
            dishes = data['dish_names']  # Will be parsed in __init__
        else:
            raise ValueError("Missing required field: either 'dishes' or 'dish_names' must be present")

        # Handle tags (may be missing in older data)
        tags = data.get('tags', "")

        # Handle notes (may be missing in older data)
        notes = data.get('notes', "")

        # Handle order_time (may be missing or in different format in older data)
        order_time = data.get('order_time')
        if not order_time:
            # Default to current time if missing
            order_time = datetime.now().isoformat()

        # Handle delivery_info field
        delivery_info = None
        if 'delivery_info' in data and data['delivery_info']:
            delivery_info = DeliveryInfo.from_dict(data['delivery_info'])

        # Handle backward compatibility with old delivery_partner and eta fields
        # This is temporary to support transition and can be removed later
        elif 'delivery_partner' in data and 'eta' in data:
            delivery_info = DeliveryInfo(
                partner_name=data.get('delivery_partner', ''),
                eta=data.get('eta', '')
            )

        # Create with validation
        return cls(
            customer_name=data['customer_name'],
            dishes=dishes,
            order_total=data['order_total'],
            status=data['status'],
            order_id=data['order_id'],
            order_time=order_time,
            tags=tags,
            notes=notes,
            status_history=data.get("status_history", [(data["order_time"], data["status"])]),
            delivery_info=delivery_info,
            assignment_history=data.get('assignment_history', [])
        )

    def are_dishes_equal(self, other_order, exact_match=True):
        """
        Compare if dishes between this order and another are the same

        If exact_match is True, compares quantities exactly
        If exact_match is False, only compares if the dish names match
        """
        # Get normalized dish lists with quantities
        if not hasattr(self, 'dishes') or not hasattr(other_order, 'dishes'):
            # Fall back to comparing dish names lists for old format orders
            my_dishes = set(self.get_dish_names())
            other_dishes = set(other_order.get_dish_names())
            return my_dishes == other_dishes

        # Normalize dishes to dictionary of name->quantity
        my_dishes = {}
        for dish in self.dishes:
            name = dish['name'].lower().strip()
            qty = dish.get('quantity', 1)
            if name in my_dishes:
                my_dishes[name] += qty
            else:
                my_dishes[name] = qty

        other_dishes = {}
        for dish in other_order.dishes:
            name = dish['name'].lower().strip()
            qty = dish.get('quantity', 1)
            if name in other_dishes:
                other_dishes[name] += qty
            else:
                other_dishes[name] = qty

        # For exact match, both dish lists must be identical
        if exact_match:
            # Must have same number of unique dishes
            if len(my_dishes) != len(other_dishes):
                return False

            # Each dish must have the same quantity in both orders
            for dish_name, qty1 in my_dishes.items():
                if dish_name not in other_dishes or other_dishes[dish_name] != qty1:
                    return False

            return True
        else:
            # For relaxed match, check if the dish sets are the same (ignoring quantities)
            return set(my_dishes.keys()) == set(other_dishes.keys())