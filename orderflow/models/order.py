import uuid
from datetime import datetime


class Order:
    """Represents a food order in the system"""

    VALID_STATUSES = ["new", "preparing", "delivered", "canceled"]
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, customer_name, dish_names, order_total, status="new",
                 order_id=None, order_time=None, tags=None, notes=None):
        self.customer_name = customer_name
        self.dish_names = dish_names if isinstance(dish_names, list) else dish_names.split(',')
        self.order_total = float(order_total)

        # Validate status
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {', '.join(self.VALID_STATUSES)}")
        self.status = status

        self.order_id = order_id or str(uuid.uuid4())

        # Handle order time
        if order_time:
            self.order_time = order_time
        else:
            # Store current time in ISO format for easy sorting and parsing
            self.order_time = datetime.now().isoformat()

        # New - Handle tags
        self.tags = []
        if tags:
            if isinstance(tags, list):
                self.tags = tags
            else:
                # Parse comma-separated tags and strip whitespace
                self.tags = [tag.strip() for tag in tags.split(',')]

        # New - Handle notes
        self.notes = notes or ""

    def to_dict(self):
        """Convert order to dictionary for storage"""
        return {
            'order_id': self.order_id,
            'customer_name': self.customer_name,
            'dish_names': ','.join(self.dish_names) if isinstance(self.dish_names, list) else self.dish_names,
            'order_total': self.order_total,
            'status': self.status,
            'order_time': self.order_time,
            'tags': ','.join(self.tags) if self.tags else "",
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data):
        """Create order instance from dictionary data"""
        # Handle tags (may be missing in older data)
        tags = data.get('tags', "")

        # Handle notes (may be missing in older data)
        notes = data.get('notes', "")

        return cls(
            customer_name=data['customer_name'],
            dish_names=data['dish_names'],
            order_total=data['order_total'],
            status=data['status'],
            order_id=data['order_id'],
            order_time=data['order_time'],
            tags=tags,
            notes=notes
        )