import json

from fastmcp import FastMCP
from typing import List, Dict, Any

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON, select, text
from dotenv import load_dotenv

import boto3
from pgvector.sqlalchemy import Vector

load_dotenv()

mcp = FastMCP("Internal_App_DB")

# ---------------------------------------------------------------------------
# 1. Async Database Connection
# ---------------------------------------------------------------------------
# Dynamic Database URL Constructor for AWS RDS vs Local
DB_HOST = os.environ.get("DATABASE_HOST")

if DB_HOST:  # If this exists, we are running in the AWS Cloud
    DB_USER = os.environ.get("DATABASE_USER")
    DB_PASS = os.environ.get("DATABASE_PASSWORD")
    DB_PORT = os.environ.get("DATABASE_PORT", "5432")
    DB_NAME = os.environ.get("DATABASE_NAME", "mdm_db")
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:  # Fall back to local .env for local testing
    DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Initialize AWS Bedrock Client
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")


def generate_embedding(text_str: str) -> list[float]:
    """Calls Amazon Titan to generate a 1024-dimension text embedding."""
    response = bedrock.invoke_model(
        body=json.dumps({"inputText": text_str}),
        modelId="amazon.titan-embed-text-v2:0",
        accept="application/json",
        contentType="application/json"
    )
    return json.loads(response.get("body").read())["embedding"]


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
    # New Vector Column for 1024-dimensional Titan embeddings
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=True)


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
        # Crucial: Enable pgvector on the RDS instance before creating tables
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
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


async def fetch_all_canonical_records() -> List[Dict[str, Any]]:
    """Retrieves all finalized Golden Records from the DB."""
    await init_db()
    async with AsyncSessionLocal() as session:
        stmt = select(CanonicalProfile)
        result = await session.execute(stmt)
        profiles = result.scalars().all()

        return [p.profile_data for p in profiles if p.profile_data]


async def fetch_canonical_by_company(company_name: str) -> List[Dict[str, Any]]:
    """Retrieves and filters canonical profiles from the DB."""
    await init_db()
    async with AsyncSessionLocal() as session:
        stmt = select(CanonicalProfile)
        result = await session.execute(stmt)
        profiles = result.scalars().all()

        return [
            p.profile_data for p in profiles
            if p.profile_data and company_name.lower() in p.profile_data.get("company_name", "").lower()
        ]


# ---------------------------------------------------------------------------
# 4. MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool
async def search_app_db(query: str) -> List[Dict[str, Any]]:
    """Search PostgreSQL internal database records by company name or user email."""
    await init_db()
    query_vector = generate_embedding(query)

    async with AsyncSessionLocal() as session:
        # ILIKE performs a case-insensitive search in PostgreSQL
        stmt = select(CustomerRecord).order_by(
            CustomerRecord.embedding.cosine_distance(query_vector)
        ).limit(5)

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
    mcp.run()
