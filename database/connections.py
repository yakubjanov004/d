import asyncpg
from config import settings
from typing import Optional

async def get_connection() -> asyncpg.Connection:
    """
    Create and return a new database connection.
    
    Returns:
        asyncpg.Connection: A new database connection
    """
    return await asyncpg.connect(settings.DB_URL)