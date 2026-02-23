import sys, os, uuid
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.database import SessionLocal
from src.models import User

db = SessionLocal()
try:
    existing = db.query(User).filter(User.email == "sarah@medrix.ai").first()
    if existing:
        print(f"User already exists: {existing.id} — {existing.name}")
    else:
        user = User(
            id=str(uuid.uuid4()),
            name="Sarah Mitchell",
            email="sarah@medrix.ai",
            date_of_birth=date(1988, 4, 14),
            blood_type="O+",
            gender="female",
            phone="+1-415-555-0192",
            address="2847 Pine Street, San Francisco, CA 94115",
            emergency_contact_name="James Mitchell",
            emergency_contact_phone="+1-415-555-0321",
            primary_care_physician="Dr. Karen Wells, MD - UCSF Medical Center",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print("User created successfully")
        print(f"  ID:                {user.id}")
        print(f"  Name:              {user.name}")
        print(f"  Email:             {user.email}")
        print(f"  DOB:               {user.date_of_birth}")
        print(f"  Blood Type:        {user.blood_type}")
        print(f"  Gender:            {user.gender}")
        print(f"  Phone:             {user.phone}")
        print(f"  Address:           {user.address}")
        print(
            f"  Emergency Contact: {user.emergency_contact_name} ({user.emergency_contact_phone})"
        )
        print(f"  Primary Care:      {user.primary_care_physician}")
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
    db.rollback()
finally:
    db.close()
