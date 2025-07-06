import uuid
import re
from datetime import datetime


class Order:
    """Represents a food order in the system with input validation"""

    VALID_STATUSES = ["new", "preparing", "delivered", "canceled"]
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, customer_name, dish_names, order_total, status="new",
                 order_id=None, order_time=None, tags=None, notes=None):
        # Validate customer name
        if not customer_name or not customer_name.strip():
            raise ValueError("Customer name cannot be empty")
        self.customer_name = customer_name.strip()

        # Validate dish names
        if not dish_names:
            raise ValueError("Dish names cannot be empty")

        # Process dish names
        if isinstance(dish_names, list):
            if not dish_names:
                raise ValueError("At least one dish must be provided")
            self.dish_names = [d.strip() for d in dish_names if d.strip()]
            if not self.dish_names:
                raise ValueError("At least one non-empty dish must be provided")
        else:
            # Split by comma and validate
            dish_list = [d.strip() for d in dish_names.split(',') if d.strip()]
            if not dish_list:
                raise ValueError("At least one non-empty dish must be provided")
            self.dish_names = dish_list

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

    def to_dict(self):
        """Convert order to dictionary for storage"""
        return {
            'order_id': self.order_id,
            'customer_name': self.customer_name,
            'dish_names': ','.join(self.dish_names),
            'order_total': self.order_total,
            'status': self.status,
            'order_time': self.order_time,
            'tags': ','.join(self.tags) if self.tags else "",
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data):
        """Create order instance from dictionary data with validation"""
        # Check required fields
        required_fields = ['order_id', 'customer_name', 'dish_names', 'order_total', 'status']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Handle tags (may be missing in older data)
        tags = data.get('tags', "")

        # Handle notes (may be missing in older data)
        notes = data.get('notes', "")

        # Handle order_time (may be missing or in different format in older data)
        order_time = data.get('order_time')
        if not order_time:
            # Default to current time if missing
            order_time = datetime.now().isoformat()

        # Create with validation
        return cls(
            customer_name=data['customer_name'],
            dish_names=data['dish_names'],
            order_total=data['order_total'],
            status=data['status'],
            order_id=data['order_id'],
            order_time=order_time,
            tags=tags,
            notes=notes
        )