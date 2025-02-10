import re

def english_data_sanitizer(data_list, wipe_numbers, replace_underscores, replace_hyphens):
    """
    This function sanitizes English data according to the specified parameters
    """

    # Build regex
    filter = []
    if wipe_numbers:
        filter.append(r'\d')
    if replace_underscores:
        filter.append(r'_')
    if replace_hyphens:
        filter.append(r'-')
    filter_pattern = '[' + ''.join(filter) + ']'

    # Sanitize data
    sanitized_data_list = [re.sub(filter_pattern, ' ', item) for item in data_list]

    return sanitized_data_list