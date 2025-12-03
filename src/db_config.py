"""
Central configuration file for the application.

This file holds all paths, settings, and configurations, so they can be
managed from a single place.
"""
from pathlib import Path

# The root directory of the source code
SRC_DIR = Path(__file__).resolve().parent
DB_FILE_PATH = SRC_DIR / "minecraft_recipes" / "minecraft_recipes.db"