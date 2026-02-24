"""
Utility to generate dummy demographic data for testing purposes.
"""

import random
from datetime import date, timedelta
from typing import Dict, Any


# ── Data pools ────────────────────────────────────────────────────────────────

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

GENDERS = ["male", "female", "other"]

CITIES = [
    ("San Francisco", "CA", "94102"),
    ("New York", "NY", "10001"),
    ("Los Angeles", "CA", "90001"),
    ("Chicago", "IL", "60601"),
    ("Houston", "TX", "77001"),
    ("Phoenix", "AZ", "85001"),
    ("Philadelphia", "PA", "19101"),
    ("San Antonio", "TX", "78201"),
    ("San Diego", "CA", "92101"),
    ("Dallas", "TX", "75201"),
    ("Austin", "TX", "78701"),
    ("Seattle", "WA", "98101"),
    ("Boston", "MA", "02101"),
    ("Denver", "CO", "80201"),
    ("Miami", "FL", "33101"),
]

STREET_NAMES = [
    "Main St",
    "Oak Ave",
    "Maple Dr",
    "Cedar Ln",
    "Pine St",
    "Elm St",
    "Washington Blvd",
    "Park Ave",
    "Lake Dr",
    "Hill Rd",
    "Forest Ln",
    "River St",
    "Mountain Way",
    "Valley Rd",
    "Sunset Blvd",
]

EMERGENCY_CONTACTS = [
    "John Smith",
    "Emily Johnson",
    "Michael Brown",
    "Sarah Davis",
    "David Wilson",
    "Lisa Anderson",
    "Robert Taylor",
    "Jennifer Martinez",
    "William Garcia",
    "Jessica Rodriguez",
    "James Lee",
    "Amanda White",
    "Daniel Harris",
    "Ashley Clark",
    "Matthew Lewis",
    "Michelle Robinson",
]

PHYSICIANS = [
    ("Dr. Sarah Johnson, MD", "Stanford Medical Center"),
    ("Dr. Michael Chen, MD", "Massachusetts General Hospital"),
    ("Dr. Emily Rodriguez, MD", "Mayo Clinic"),
    ("Dr. David Williams, MD", "Cleveland Clinic"),
    ("Dr. Lisa Anderson, MD", "Johns Hopkins Hospital"),
    ("Dr. Robert Martinez, MD", "UCLA Medical Center"),
    ("Dr. Jennifer Lee, MD", "NYU Langone Health"),
    ("Dr. James Brown, MD", "UCSF Medical Center"),
    ("Dr. Amanda Davis, MD", "Mount Sinai Hospital"),
    ("Dr. Christopher Wilson, MD", "Cedars-Sinai Medical Center"),
]


# ── Generator Functions ───────────────────────────────────────────────────────


def generate_random_dob(min_age: int = 18, max_age: int = 80) -> date:
    """Generate a random date of birth between min_age and max_age years ago."""
    today = date.today()
    days_in_range = (max_age - min_age) * 365
    random_days = random.randint(0, days_in_range)
    years_ago = min_age * 365 + random_days
    return today - timedelta(days=years_ago)


def generate_phone_number() -> str:
    """Generate a random US phone number."""
    area_code = random.randint(200, 999)
    prefix = random.randint(200, 999)
    line = random.randint(1000, 9999)
    return f"+1-{area_code}-{prefix}-{line:04d}"


def generate_address() -> str:
    """Generate a random US address."""
    street_number = random.randint(100, 9999)
    street_name = random.choice(STREET_NAMES)
    city, state, zipcode = random.choice(CITIES)
    return f"{street_number} {street_name}, {city}, {state} {zipcode}"


def generate_emergency_contact() -> tuple[str, str]:
    """Generate emergency contact name and phone number."""
    name = random.choice(EMERGENCY_CONTACTS)
    phone = generate_phone_number()
    return name, phone


def generate_primary_care_physician() -> str:
    """Generate a primary care physician name and facility."""
    doctor, facility = random.choice(PHYSICIANS)
    return f"{doctor} - {facility}"


def generate_dummy_demographics(user_name: str = None) -> Dict[str, Any]:
    """
    Generate a complete set of dummy demographic data for testing.

    Args:
        user_name: Optional user name to derive emergency contact from

    Returns:
        Dictionary containing all demographic fields
    """
    emergency_name, emergency_phone = generate_emergency_contact()

    demographics = {
        "date_of_birth": generate_random_dob(),
        "blood_type": random.choice(BLOOD_TYPES),
        "gender": random.choice(GENDERS),
        "phone": generate_phone_number(),
        "address": generate_address(),
        "emergency_contact_name": emergency_name,
        "emergency_contact_phone": emergency_phone,
        "primary_care_physician": generate_primary_care_physician(),
    }

    return demographics


# ── Test/Debug ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test the generator
    print("🧪 Testing Dummy Demographics Generator\n")

    for i in range(3):
        print(f"Sample {i+1}:")
        demo = generate_dummy_demographics("Test User")
        for key, value in demo.items():
            print(f"  {key}: {value}")
        print()
