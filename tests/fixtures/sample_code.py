"""Sample Python file with intentional issues for testing."""


def calculate_total(items):
    """Calculate total price of items."""
    unused_var = 0  # SonarQube would flag this as unused
    total = 0
    for item in items:
        total += item["price"]
    return total


def process_data(data):
    """Process data with duplicated string literal."""
    if data == "production":  # Duplicated literal
        print("Running in production mode")
    elif data == "production":  # Duplicated literal
        print("Production environment detected")
    elif data == "production":  # Duplicated literal again
        print("Production mode active")
