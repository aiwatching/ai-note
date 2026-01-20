#!/usr/bin/env python3
"""Initialize the database with tables and default data."""
import sys
from pathlib import Path

# Add the service app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "service"))

from app.database import init_db, SessionLocal
from app.models.user import User


def main():
    """Initialize database and create default user."""
    print("Initializing database...")
    init_db()
    print("Database tables created successfully.")

    # Create default user
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(id=1, username="default_user", email="default@example.com")
            db.add(user)
            db.commit()
            print("Default user created.")
        else:
            print("Default user already exists.")
    finally:
        db.close()

    print("Database initialization complete!")


if __name__ == "__main__":
    main()
