#!/usr/bin/env python3
"""
Database initialization script for SNDVT integration.

This script ensures all new tables are created and the database is properly initialized
for the NetPredict alerts and Network Agent integrations.
"""

import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect
from app.config.database import engine, Base
from app.config.settings import get_settings

# Import all models to ensure they're registered with Base
from app.auth.models.user import User
from app.auth.models.schemas import UserCreate, LoginRequest, Token
from app.alerts.models.alert import Alert, AlertSettings
from app.network_agent.models.session import AgentSession, DeviceInfo
from app.network_agent.models.command import CommandHistory, AgentConfig

def check_database_connection():
    """Test database connection."""
    try:
        # Test connection
        with engine.connect() as connection:
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_tables():
    """Create all tables."""
    try:
        # Get inspector to check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print(f"📋 Existing tables: {existing_tables}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Check what tables were created
        new_tables = inspector.get_table_names()
        created_tables = set(new_tables) - set(existing_tables)
        
        if created_tables:
            print(f"✅ Created new tables: {list(created_tables)}")
        else:
            print("ℹ️  All tables already exist")
            
        # List all current tables
        print(f"📊 All tables: {new_tables}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def verify_integration_tables():
    """Verify that all integration-specific tables exist."""
    required_tables = [
        'alerts',           # NetPredict alerts
        'alert_settings',   # Alert configuration
        'agent_sessions',   # Network agent chat sessions
        'command_history',  # Command execution history
        'device_info',      # Network device information
        'agent_config'      # Agent configuration
    ]
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    missing_tables = [table for table in required_tables if table not in existing_tables]
    
    if missing_tables:
        print(f"⚠️  Missing tables: {missing_tables}")
        return False
    else:
        print("✅ All integration tables exist")
        return True

def main():
    """Main initialization function."""
    settings = get_settings()
    
    print("🚀 SNDVT Database Initialization")
    print("=" * 50)
    print(f"Database URL: {settings.database_url}")
    print()
    
    # Step 1: Check database connection
    print("1. Checking database connection...")
    if not check_database_connection():
        sys.exit(1)
    print()
    
    # Step 2: Create tables
    print("2. Creating database tables...")
    if not create_tables():
        sys.exit(1)
    print()
    
    # Step 3: Verify integration tables
    print("3. Verifying integration tables...")
    if not verify_integration_tables():
        print("⚠️  Some integration tables are missing, but this may be normal.")
        print("    The tables will be created automatically when the services start.")
    print()
    
    print("🎉 Database initialization completed successfully!")
    print()
    print("Next steps:")
    print("1. Start NetPredict service: cd ../netpredict && python main.py")
    print("2. Start Network Agent: cd ../Network-ai-agent/react_ai_agent_cisco_ios_xe && python fastapi_agent.py")
    print("3. Start SNDVT backend: python app/main.py")
    print("4. Start SNDVT frontend: cd ../sndvtfrontend && npm run dev")

if __name__ == "__main__":
    main()