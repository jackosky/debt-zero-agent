"""Sample Python code with SonarQube issues for testing."""


def calculate_price(items):
    """Calculate total price with unused variable."""
    tax_rate = 0.1  # SonarQube: S1481 - unused variable
    total = 0
    for item in items:
        total += item["price"]
    return total


def get_environment():
    """Function with duplicated string literals."""
    # SonarQube: S1192 - duplicated literal
    if True:
        print("production")
        return "production"
    else:
        return "production"


class DataProcessor:
    """Class with code smell issues."""
    
    def process(self, data):
        """Method with too many nested blocks."""
        # SonarQube: S134 - too many nested blocks
        if data:
            if len(data) > 0:
                if isinstance(data, list):
                    if data[0]:
                        if "key" in data[0]:
                            return data[0]["key"]
        return None
    
    def validate(self, value):
        """Method with identical branches."""
        # SonarQube: S1871 - identical branches
        if value > 10:
            return True
        else:
            return True
