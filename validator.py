"""
validator.py - Validate SQL before execution.
"""
import re

ALLOWED = {"SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH"}

BLOCKED = [
    r"\bPRAGMA\b", r"\bATTACH\b", r"\bDETACH\b", r"\bVACUUM\b",
    r"\bBEGIN\b", r"\bCOMMIT\b", r"\bROLLBACK\b", r"\bload_extension\b",
]


def validate(sql):
    """Returns (ok, error_message)."""
    sql = sql.strip()
    if not sql:
        return False, "Empty SQL."

    # Block multiple statements
    if ";" in sql.rstrip(";"):
        return False, "Only one SQL statement allowed at a time."

    upper = sql.upper()
    for pattern in BLOCKED:
        if re.search(pattern, upper, re.IGNORECASE):
            return False, f"Blocked operation: {pattern}"

    first = upper.split()[0] if upper.split() else ""
    if first not in ALLOWED:
        return False, f"Statement type '{first}' is not allowed."

    return True, ""
