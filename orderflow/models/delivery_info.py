class DeliveryInfo:
    """Class to represent delivery information"""

    def __init__(self, partner_name, eta):
        """Initialize a DeliveryInfo instance"""
        self.partner_name = partner_name
        self.eta = eta

    def to_dict(self):
        """Convert DeliveryInfo to dictionary for serialization"""
        return {
            "partner_name": self.partner_name,
            "eta": self.eta
        }

    @classmethod
    def from_dict(cls, data):
        """Create a DeliveryInfo instance from dictionary"""
        if not data:
            return None
        return cls(
            partner_name=data.get("partner_name"),
            eta=data.get("eta")
        )
