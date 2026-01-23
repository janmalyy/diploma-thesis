import json


def write_json(data: dict, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_json_structure(data, text_threshold: int = 50) -> dict | list | str:
    """
    Recursively analyzes JSON to find unique categorical values and free-text.

    This function collapses lists of objects into a single-element list
    containing a merged schema of all objects found in that list.
    """
    if isinstance(data, list):
        if not data:
            return []

        # If the list contains dictionaries, merge them into one structural template
        if any(isinstance(item, dict) for item in data):
            merged_dict = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                item_struct = get_json_structure(item, text_threshold)
                for key, value in item_struct.items():
                    if key not in merged_dict:
                        merged_dict[key] = value
                    else:
                        # Merge logic: prioritize 'free text' or aggregate unique categories
                        if merged_dict[key] == "free text" or value == "free text":
                            merged_dict[key] = "free text"
                        elif isinstance(merged_dict[key], list) and isinstance(value, list):
                            for v in value:
                                if v not in merged_dict[key]:
                                    merged_dict[key].append(v)
            return [merged_dict]

        # If it's a list of primitives, return unique values
        unique_values = []
        for item in data:
            # Flatten or handle nested simple lists (e.g., keywords)
            processed = get_json_structure(item, text_threshold)
            val_to_add = processed[0] if isinstance(processed, list) and len(processed) == 1 else processed
            if val_to_add not in unique_values:
                unique_values.append(val_to_add)
        return unique_values

    if isinstance(data, dict):
        return {k: get_json_structure(v, text_threshold) for k, v in data.items()}

    if isinstance(data, str) and len(data) > text_threshold:
        return "free text"

    return [data]


def print_structure(data,
                    indent: int = 0,
                    list_threshold: int = 5) -> None:
    """
    Recursively prints the summarized JSON structure.

    Expands lists that contain structural dictionaries (like 'contents')
    while keeping simple categorical lists on one line.
    """
    prefix = " " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            # Case 1: Value is a list containing a dictionary (Structural List)
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                print(f"{prefix}{key}:")
                print_structure(value[0], indent + 1, list_threshold)

            # Case 2: Value is a dictionary (Nested Object)
            elif isinstance(value, dict):
                print(f"{prefix}{key}:")
                print_structure(value, indent + 1, list_threshold)

            # Case 3: Value is a simple list or primitive
            else:
                print(f"{prefix}{key}: ", end="")
                print_structure(value, 0, list_threshold)

    elif isinstance(data, list):
        # Truncate and print categorical data on one line
        if len(data) > list_threshold:
            head = [str(x) for x in data[:2]]
            tail = [str(x) for x in data[-2:]]
            print(f"[{', '.join(head)}, ..., {', '.join(tail)}]")
        else:
            # Clean up the output to look like pseudo-json
            formatted = json.dumps(data, ensure_ascii=False)
            print(formatted)

    else:
        # Handle 'free text' strings or single values
        if isinstance(data, str) and data == "free text":
            print(f'"{data}"')
        else:
            print(json.dumps(data, ensure_ascii=False))


def get_all_values_for_key(data: dict | list, target_key: str) -> list:
    """
    Recursively searches for a key in a JSON-like structure and returns all unique values.
    Important: It merges all values found into a single list.
    It does not distinguish the nested structure level, it can happen that the same target_key is used multiple times in different contexts.
    Args:
        data: The dictionary or list to search through.
        target_key: The specific key to find values for.

    Returns:
        A list of unique values associated with the target_key found anywhere in the data.
    """
    results = []

    def _add_unique(value) -> None:
        """Helper to add value to results if not already present."""
        if value not in results:
            if isinstance(value, str):
                results.append(value)
            elif isinstance(value, list):
                results.extend(value)

    if isinstance(data, dict):
        for key, value in data.items():
            if key == target_key:
                _add_unique(value)

            # Recurse into nested structures
            if isinstance(value, (dict, list)):
                nested_results = get_all_values_for_key(value, target_key)
                for val in nested_results:
                    _add_unique(val)

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                nested_results = get_all_values_for_key(item, target_key)
                for val in nested_results:
                    _add_unique(val)

    return results


if __name__ == '__main__':
    with open(r"SIBiLS_fetch_pmc.json", "r") as f:
        data = json.load(f)
    structure = get_json_structure(data)
    # print(structure)
    # print_structure(structure, indent=2, list_threshold=20)
    print(get_all_values_for_key(structure, "tag"))
