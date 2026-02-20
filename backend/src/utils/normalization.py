"""Data normalization utilities for clinical data extraction."""

import re
from typing import Optional, Union


def normalize_height(value: Union[str, int, float]) -> Optional[float]:
    """
    Convert height to cm (centimeters).

    Handles formats:
    - Feet'Inches: "5'10\"" → 177.8
    - Feet'Inches without quotes: "5'10" → 177.8
    - Inches: "70 in" → 177.8
    - Centimeters: "178 cm" → 178.0
    - Numeric (assumes cm): 178 → 178.0

    Args:
        value: Height in various formats

    Returns:
        Height in cm as float, or None if cannot parse
    """
    if value is None:
        return None

    # Already numeric (assume cm)
    if isinstance(value, (int, float)):
        return float(value)

    value_str = str(value).strip().replace("″", '"').replace("′", "'")

    # Handle feet'inches" format (5'10", 5'10, 5 ft 10 in)
    patterns = [
        r"(\d+)['\u2019\u2032]\s*(\d+)[\"\u201d\u2033]?",  # 5'10" or 5'10
        r"(\d+)\s*(?:ft|feet)\s*(\d+)\s*(?:in|inches)?",  # 5 ft 10 in
    ]

    for pattern in patterns:
        match = re.match(pattern, value_str, re.IGNORECASE)
        if match:
            feet = int(match.group(1))
            inches = int(match.group(2))
            total_inches = feet * 12 + inches
            return round(total_inches * 2.54, 1)

    # Handle numeric with unit
    match = re.match(
        r"([\d.]+)\s*(cm|centimeters?|in|inches?)", value_str, re.IGNORECASE
    )
    if match:
        val = float(match.group(1))
        unit = match.group(2).lower()
        if unit.startswith("cm"):
            return round(val, 1)
        elif unit.startswith("in"):
            return round(val * 2.54, 1)

    # Try pure numeric string
    try:
        return round(float(value_str), 1)
    except ValueError:
        return None


def normalize_weight(
    value: Union[str, int, float], target_unit: str = "kg"
) -> Optional[dict]:
    """
    Normalize weight to consistent format with unit.

    Args:
        value: Weight as string or number
        target_unit: Target unit ('kg' or 'lbs'), default 'kg'

    Returns:
        Dict with 'value' and 'unit' keys, or None if cannot parse
    """
    if value is None:
        return None

    # Numeric without unit (assume kg)
    if isinstance(value, (int, float)):
        return {"value": float(value), "unit": target_unit}

    value_str = str(value).strip()

    # Extract numeric value and unit
    match = re.match(
        r"([\d.]+)\s*(kg|kilograms?|lbs?|pounds?)", value_str, re.IGNORECASE
    )
    if match:
        val = float(match.group(1))
        unit = match.group(2).lower()

        # Normalize unit name
        if unit.startswith("kg"):
            unit = "kg"
        elif unit.startswith("lb") or unit.startswith("pound"):
            unit = "lbs"

        # Convert if needed
        if target_unit == "kg" and unit == "lbs":
            val = round(val * 0.453592, 1)
            unit = "kg"
        elif target_unit == "lbs" and unit == "kg":
            val = round(val * 2.20462, 1)
            unit = "lbs"

        return {"value": val, "unit": unit}

    # Try pure numeric
    try:
        return {"value": round(float(value_str), 1), "unit": target_unit}
    except ValueError:
        return None


def normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize date to ISO format (YYYY-MM-DD).

    Handles formats:
    - "Jan 15, 2024" → "2024-01-15"
    - "01/15/2024" → "2024-01-15"
    - "2024-01-15" → "2024-01-15" (already ISO)
    - "15-Jan-2024" → "2024-01-15"

    Args:
        date_str: Date in various formats

    Returns:
        ISO formatted date string, or None if cannot parse
    """
    if not date_str:
        return None

    try:
        from dateutil import parser

        parsed = parser.parse(date_str)
        return parsed.strftime("%Y-%m-%d")
    except:
        return None


def normalize_temperature(
    value: Union[str, int, float], source_unit: Optional[str] = None
) -> Optional[dict]:
    """
    Normalize temperature with unit detection.

    Args:
        value: Temperature value
        source_unit: Source unit if known ('F', 'C')

    Returns:
        Dict with 'value' and 'unit', or None
    """
    if value is None:
        return None

    # Numeric with explicit unit
    if isinstance(value, (int, float)):
        if source_unit and source_unit.upper() in ["F", "C"]:
            return {"value": float(value), "unit": source_unit.upper()}
        # Assume Fahrenheit if in normal body temp range
        return {"value": float(value), "unit": "F" if 95 <= value <= 105 else "C"}

    value_str = str(value).strip()

    # Extract value and unit
    match = re.match(r"([\d.]+)\s*[°]?\s*([FCfc])", value_str)
    if match:
        val = float(match.group(1))
        unit = match.group(2).upper()
        return {"value": val, "unit": unit}

    # Try numeric only
    try:
        val = float(value_str)
        return {"value": val, "unit": "F" if 95 <= val <= 105 else "C"}
    except ValueError:
        return None


# Test cases
if __name__ == "__main__":
    # Height tests
    assert normalize_height("5'10\"") == 177.8
    assert normalize_height("5'10") == 177.8
    assert normalize_height("70 in") == 177.8
    assert normalize_height("178 cm") == 178.0
    assert normalize_height(178) == 178.0
    assert normalize_height("6 ft 2 in") == 187.96

    # Weight tests
    assert normalize_weight("195 lbs") == {"value": 195.0, "unit": "lbs"}
    assert normalize_weight("70 kg") == {"value": 70.0, "unit": "kg"}
    assert normalize_weight(70) == {"value": 70.0, "unit": "kg"}

    # Date tests
    assert normalize_date("Jan 15, 2024") == "2024-01-15"
    assert normalize_date("01/15/2024") == "2024-01-15"
    assert normalize_date("2024-01-15") == "2024-01-15"

    # Temperature tests
    assert normalize_temperature("98.6°F") == {"value": 98.6, "unit": "F"}
    assert normalize_temperature("37 C") == {"value": 37.0, "unit": "C"}
    assert normalize_temperature(98.6) == {"value": 98.6, "unit": "F"}

    print("✅ All normalization tests passed!")
