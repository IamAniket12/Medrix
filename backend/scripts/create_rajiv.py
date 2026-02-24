import sys, os, uuid
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.database import SessionLocal
from src.models import User

db = SessionLocal()
try:
    existing = db.query(User).filter(User.email == "rajiv@medrix.ai").first()
    if existing:
        print(f"User already exists: {existing.id} — {existing.name}")
    else:
        user = User(
            id=str(uuid.uuid4()),
            name="Rajiv Kumar",
            email="rajiv@medrix.ai",
            date_of_birth=date(1974, 3, 15),
            blood_type="A+",
            gender="male",
            phone="+91-98765-43210",
            address="45 MG Road, Bangalore, Karnataka 560001, India",
            emergency_contact_name="Priya Kumar",
            emergency_contact_phone="+91-98765-43211",
            primary_care_physician="Dr. Amit Sharma, MD - Apollo Hospital",
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
