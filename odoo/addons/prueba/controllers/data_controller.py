import re
import string


def english_data_sanitizer(data_list, wipe_punctuation, wipe_numbers):
    """
    This function sanitizes English data according to the specified parameters
    """
    # Build regex
    filter = []
    # Whipe numbers
    if wipe_numbers:
        filter.append(r'\d')
    # Wipe punctuation signs
    if wipe_punctuation:
        filter.append(re.escape(string.punctuation))

    # Build the final pattern
    filter_pattern = r'[' + ''.join(filter) + ']'

    # Sanitize data
    sanitized_data_list = [re.sub(r'\s+', ' ', re.sub(filter_pattern, ' ', item)).strip() for item in data_list]
    return sanitized_data_list