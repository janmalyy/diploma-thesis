import re


def is_safe_query(query: str) -> bool:
    """
    Validates if a Cypher query is safe to execute.

    Args:
        query: The Cypher query string to validate

    Returns:
        bool: True if the query is considered safe, False otherwise
    """
    stripped = re.sub(r"(?m)//.*?$", "", query).strip().upper()
    return (stripped.startswith(("MATCH", "WITH", "RETURN"))
            and not re.search(r"\bCALL\s+(dbms|apoc)\b", query, re.IGNORECASE))