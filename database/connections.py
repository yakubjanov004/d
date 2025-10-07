# database/connections.py
# Database connection utilities

from config import settings

def get_connection_url() -> str:
    """
    Get the database connection URL from settings.
    
    Returns:
        str: The database connection URL
    """
    return settings.DB_URL
