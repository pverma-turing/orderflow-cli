import json
from pathlib import Path


def get_active_restaurant_id():
    """Get the active restaurant ID from config.

    Returns:
        str: The active restaurant ID

    Raises:
        ValueError: If no active restaurant is set or the ID is invalid
    """
    config_path = Path('.orderflowrc')

    # Check if config file exists
    if not config_path.exists():
        raise ValueError(
            "No active restaurant selected. Please run 'restaurant use --id <restaurant_id>' first."
        )

    try:
        # Load the config file
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Get the active restaurant ID
        restaurant_id = config.get('active_restaurant')
        if not restaurant_id:
            raise ValueError(
                "No active restaurant configured. Please run 'restaurant use --id <restaurant_id>' first."
            )

        # Validate that the restaurant exists in the registry
        restaurants_file = Path("data/restaurants.json")
        if not restaurants_file.exists():
            raise ValueError(
                f"Restaurant registry file not found. Please run 'restaurant register' first."
            )

        with open(restaurants_file, 'r') as f:
            restaurants = json.load(f)

        # Check if the restaurant ID exists
        if not any(restaurant['id'] == restaurant_id for restaurant in restaurants):
            raise ValueError(
                f"Selected restaurant ID '{restaurant_id}' not found in registry. "
                "It may have been deleted. Please run 'restaurant use --id <id>' to select a valid restaurant."
            )

        return restaurant_id

    except json.JSONDecodeError:
        raise ValueError(
            "Config file is corrupted. Please run 'restaurant use --id <restaurant_id>' to reset."
        )
    except IOError as e:
        raise ValueError(
            f"Error reading configuration: {e}. Please run 'restaurant use --id <restaurant_id>' to try again."
        )