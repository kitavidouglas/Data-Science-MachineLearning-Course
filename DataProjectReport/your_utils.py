# your_utils.py

def ensure_str(val):
    """
    Safely converts a value to a string.
    Handles None, numbers, dicts, and lists gracefully.
    """
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        return ", ".join(map(str, val))
    if isinstance(val, dict):
        return str(val)
    try:
        return str(val).strip()
    except Exception:
        return ""
