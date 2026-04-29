import asyncio
import sys
import os

# Add the project root to sys.path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import text
from app.db.session import engine
from app.models.models import Base

async def init_db():
    async with engine.begin() as conn:
        # Create pgvector extension
        print("Creating pgvector extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Create all tables
        print("Creating all tables...")
        # In a real scenario with Alembic, we'd use migrations. 
        # For the first run, we can create them directly.
        await conn.run_sync(Base.metadata.create_all)
        
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
