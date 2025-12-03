"""
Handles database connections and session management.

This module acts as a factory for creating database sessions, ensuring that
other parts of the application don't need to know the specific path to the
database file. It promotes loose coupling.
"""
from src.config.settings import DB_PATH
from .repository import RecipeDB

# A global variable to hold a single, reusable instance of the database connection.
# This is a simple way to implement a Singleton pattern for the DB connection.
_db_instance = None

def get_db() -> RecipeDB:
    """Returns a singleton instance of the RecipeDB."""
    global _db_instance
    if _db_instance is None:
        print(f"DATABASE: Initializing connection to {DB_PATH}...")
        _db_instance = RecipeDB(str(DB_PATH))
    return _db_instance