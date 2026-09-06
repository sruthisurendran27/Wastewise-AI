"""MongoDB connection management using Motor (async driver)."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> AsyncIOMotorDatabase:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri, tz_aware=True)
    return _client[settings.mongo_db_name]


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency that returns the active database handle."""
    if _client is None:
        raise RuntimeError("MongoDB connection has not been initialized")
    return _client[settings.mongo_db_name]


async def ensure_indexes() -> None:
    """Idempotently create the indexes the app relies on."""
    db = await connect_db()
    await db["users"].create_index("email", unique=True)
    await db["recyclers"].create_index([("location", "2dsphere")])
    await db["waste_scans"].create_index([("user_id", 1), ("created_at", -1)])
    await db["activities"].create_index([("user_id", 1), ("created_at", -1)])
    await db["diy_ideas_cache"].create_index("final_label", unique=True)
    await db["disposal_guides"].create_index("waste_type", unique=True)