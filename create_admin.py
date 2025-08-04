#!/usr/bin/env python3
"""Script to create an initial admin user."""

import os
import sys
from sqlalchemy.orm import Session

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal, engine, Base
from app.auth.services.auth_service import AuthService


def create_admin_user():
    """Create an admin user if one doesn't exist."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if any superuser exists
        from app.auth.models.user import User
        existing_admin = db.query(User).filter(User.is_superuser == True).first()
        
        if existing_admin:
            print(f"Admin user already exists: {existing_admin.email}")
            return
        
        # Get admin details
        email = input("Enter admin email: ").strip()
        username = input("Enter admin username: ").strip()
        full_name = input("Enter admin full name (optional): ").strip() or None
        password = input("Enter admin password: ").strip()
        
        if not email or not username or not password:
            print("Email, username, and password are required!")
            return
        
        # Create admin user
        admin_user = AuthService.create_user(
            db=db,
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            is_superuser=True
        )
        
        print(f"Admin user created successfully!")
        print(f"ID: {admin_user.id}")
        print(f"Email: {admin_user.email}")
        print(f"Username: {admin_user.username}")
        print(f"Full Name: {admin_user.full_name}")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()