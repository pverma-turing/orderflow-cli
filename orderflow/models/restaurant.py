class Restaurant:
    """Model representing a restaurant in the OrderFlow system."""

    def __init__(self, id, name, cuisine=None, location=None, contact=None):
        """Initialize a restaurant.

        Args:
            id (str): Unique restaurant identifier
            name (str): Restaurant name
            cuisine (str, optional): Type of cuisine
            location (str, optional): Restaurant location
            contact (str, optional): Contact information
        """
        self.id = id
        self.name = name
        self.cuisine = cuisine
        self.location = location
        self.contact = contact

    @classmethod
    def from_dict(cls, data):
        """Create a Restaurant object from a dictionary.

        Args:
            data (dict): Dictionary with restaurant data

        Returns:
            Restaurant: A new Restaurant instance
        """
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            cuisine=data.get('cuisine'),
            location=data.get('location'),
            contact=data.get('contact')
        )

    def to_dict(self):
        """Convert Restaurant instance to a dictionary.

        Returns:
            dict: Dictionary representation of the restaurant
        """
        restaurant_dict = {
            'id': self.id,
            'name': self.name
        }

        # Add optional fields if they exist
        if self.cuisine:
            restaurant_dict['cuisine'] = self.cuisine
        if self.location:
            restaurant_dict['location'] = self.location
        if self.contact:
            restaurant_dict['contact'] = self.contact

        return restaurant_dict