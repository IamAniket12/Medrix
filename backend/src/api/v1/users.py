"""User authentication routes — email-only login / register."""

import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.user import User
from src.utils.dummy_demographics import generate_dummy_demographics

router = APIRouter(prefix="/users", tags=["users"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str


class RegisterRequest(BaseModel):
    email: str
    name: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/login", response_model=UserResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Email-only login. Returns the user record if the email exists.
    Raises 404 if not found so the frontend can prompt to register.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with that email. Please create an account.",
        )
    return user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new user with name + email.
    Also generates dummy demographic data for testing purposes.
    Returns 409 if email is already registered.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please log in.",
        )

    # Generate dummy demographics for testing
    print(f"🎲 Generating dummy demographics for {payload.name}...")
    demographics = generate_dummy_demographics(user_name=payload.name)

    # Add a small delay to simulate processing (for progress bar visibility)
    await asyncio.sleep(2.0)

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        name=payload.name.strip(),
        # Add demographic data
        date_of_birth=demographics["date_of_birth"],
        blood_type=demographics["blood_type"],
        gender=demographics["gender"],
        phone=demographics["phone"],
        address=demographics["address"],
        emergency_contact_name=demographics["emergency_contact_name"],
        emergency_contact_phone=demographics["emergency_contact_phone"],
        primary_care_physician=demographics["primary_care_physician"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"✅ User created with dummy demographics:")
    print(f"   - DOB: {user.date_of_birth}")
    print(f"   - Blood Type: {user.blood_type}")
    print(f"   - Gender: {user.gender}")
    print(f"   - Emergency Contact: {user.emergency_contact_name}")

    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Fetch a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return user
