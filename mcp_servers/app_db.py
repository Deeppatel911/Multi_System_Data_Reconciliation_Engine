import json

from fastmcp import FastMCP
from typing import List, Dict, Any

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON, select
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("Internal_App_DB")

# ---------------------------------------------------------------------------
# 1. Async Database Connection
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# 2. Object Relational Mapper (ORM) Schema
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class CustomerRecord(Base):
    __tablename__ = "customer_records"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    company: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean)
    last_login: Mapped[str] = mapped_column(String, nullable=True)


class CanonicalProfile(Base):
    __tablename__ = "canonical_profiles"

    canonical_id: Mapped[str] = mapped_column(String, primary_key=True)
    profile_data: Mapped[dict] = mapped_column(JSON)  # Stores the entire output payload


# ---------------------------------------------------------------------------
# 3. Database Initialization & Seeding
# ---------------------------------------------------------------------------
async def init_db():
    """Creates tables and seeds initial data for testing."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed data so our previous queries still work
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CustomerRecord))
        if not result.scalars().first():
            session.add_all([
                CustomerRecord(user_id="usr_98124", company="Acme", email="admin@acme.io", is_active=False,
                               last_login="2026-07-10"),
                CustomerRecord(user_id="usr_77211", company="Globex", email="admin@globex.io", is_active=True,
                               last_login="2026-08-16")
            ])
            await session.commit()


# ---------------------------------------------------------------------------
# 4. MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool
async def search_app_db(query: str) -> List[Dict[str, Any]]:
    """Search PostgreSQL internal database records by company name or user email."""
    await init_db()
    async with AsyncSessionLocal() as session:
        # ILIKE performs a case-insensitive search in PostgreSQL
        stmt = select(CustomerRecord).where(
            CustomerRecord.company.ilike(f"%{query}%") |
            CustomerRecord.email.ilike(f"%{query}%")
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        return [{
            "user_id": r.user_id,
            "company": r.company,
            "email": r.email,
            "is_active": r.is_active,
            "last_login": r.last_login
        } for r in records]


@mcp.tool
async def save_canonical_profile(profile: Dict[str, Any]) -> str:
    """Persist a resolved UnifiedCustomerProfile to the canonical profile store."""
    await init_db()
    async with AsyncSessionLocal() as session:
        new_profile = CanonicalProfile(
            canonical_id=profile.get("canonical_id"),
            profile_data=profile
        )
        session.add(new_profile)
        await session.commit()

    return json.dumps({
        "success": True,
        "canonical_id": profile.get("canonical_id")
    })

if __name__ == "__main__":
    import asyncio
    # Initialize the DB schema before starting the server
    asyncio.run(init_db())
    mcp.run()
