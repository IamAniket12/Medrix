"""
Script to populate demographic data for demo_user_001
"""

import sys
import os
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import SessionLocal
from src.models import User


def populate_demographics():
    """Populate demographic data for demo_user_001"""
    db = SessionLocal()

    try:
        # Find demo user
        user = db.query(User).filter(User.id == "demo_user_001").first()

        if not user:
            print("❌ User demo_user_001 not found")
            return

        # Update demographics
        user.date_of_birth = date(1985, 3, 15)
        user.blood_type = "A+"
        user.gender = "male"
        user.phone = "+1-555-0123"
        user.address = "123 Medical Plaza, San Francisco, CA 94102"
        user.emergency_contact_name = "Aniket Dixit"
        user.emergency_contact_phone = "+1-555-0456"
        user.primary_care_physician = "Dr. Sarah Smith, MD - Stanford Medical Center"

        db.commit()

        print("✓ Demographics populated for demo_user_001")
        print(f"  Name: {user.name}")
        print(f"  DOB: {user.date_of_birth}")
        print(f"  Blood Type: {user.blood_type}")
        print(f"  Gender: {user.gender}")
        print(f"  Phone: {user.phone}")
        print(
            f"  Emergency Contact: {user.emergency_contact_name} ({user.emergency_contact_phone})"
        )
        print(f"  Primary Care: {user.primary_care_physician}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    populate_demographics()
