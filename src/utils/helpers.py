def format_ecg_data(ecg_data):
    # Function to format ECG data for display
    return [round(value, 2) for value in ecg_data]

def validate_user_input(input_data, expected_type):
    # Function to validate user input
    if not isinstance(input_data, expected_type):
        raise ValueError(f"Input must be of type {expected_type.__name__}")
    return True

def calculate_average(values):
    # Function to calculate the average of a list of values
    if not values:
        return 0
    return sum(values) / len(values)