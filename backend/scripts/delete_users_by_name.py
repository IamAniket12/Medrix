"""
Script to delete specific users by name from the database.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import SessionLocal
from src.models.user import User


def delete_users_by_name(names: list[str]):
    """Delete users by their names."""
    db = SessionLocal()

    try:
        deleted_count = 0

        for name in names:
            # Find users with this name (case-insensitive)
            users = db.query(User).filter(User.name.ilike(f"%{name}%")).all()

            if not users:
                print(f"⚠️  No user found with name containing '{name}'")
                continue

            for user in users:
                print(f"\n🗑️  Deleting user:")
                print(f"   ID: {user.id}")
                print(f"   Name: {user.name}")
                print(f"   Email: {user.email}")
                print(f"   Date of Birth: {user.date_of_birth}")
                print(f"   Blood Type: {user.blood_type}")

                # Delete the user (cascade will handle related records)
                db.delete(user)
                deleted_count += 1

        if deleted_count > 0:
            confirm = input(
                f"\n⚠️  Are you sure you want to delete {deleted_count} user(s)? (yes/no): "
            )
            if confirm.lower() == "yes":
                db.commit()
                print(f"\n✅ Successfully deleted {deleted_count} user(s)")
            else:
                db.rollback()
                print("\n❌ Deletion cancelled")
        else:
            print("\n❌ No users found to delete")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Delete users with names "abhishek" and "aishwarya"
    names_to_delete = ["abhishek", "aishwarya"]

    print("=" * 70)
    print("DELETE USERS BY NAME")
    print("=" * 70)
    print(f"\nSearching for users with names: {', '.join(names_to_delete)}\n")

    delete_users_by_name(names_to_delete)
