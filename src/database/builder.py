import json
import sqlite3
from pathlib import Path
from typing import List, Dict
from collections import Counter

from src.database.repository import RecipeDB


# --- Flexible Ingredient Types ---
# A single item can be a string or a dictionary (e.g., {"item": "..."})
Item = Dict[str, str] | str
# An ingredient definition can be a single item or a list of items
Ingredient = Item | List[Item]


# --- Helper Functions ---

def get_clean_name(item_id: str) -> str:
    """Converts 'minecraft:chiseled_stone_bricks' to 'Chiseled Stone Bricks'."""
    return item_id.split(':')[-1].replace('_', ' ').title()


def get_all_ingredient_ids(ingredient: Ingredient) -> List[str]:
    """Recursively extracts all item IDs from an ingredient definition into a flat list."""
    ids = []
    if isinstance(ingredient, list):
        # For a list of choices, just pick the first one to represent the slot.
        # This simplifies counting for craftable recipes.
        if ingredient:
            ids.extend(get_all_ingredient_ids(ingredient[0]))
    elif isinstance(ingredient, dict):
        item_id = ingredient.get('item') or ingredient.get('tag')
        if item_id:
            ids.append(item_id)
    elif isinstance(ingredient, str):
        ids.append(ingredient)
    return ids  # Return the full list to preserve counts


# --- Main Logic ---

def create_database(db_path: str, recipes_path: Path):
    """Reads all recipe JSONs and populates a SQLite database."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS recipes")
    cur.execute("""
        CREATE TABLE recipes (
            id INTEGER PRIMARY KEY,
            result_id TEXT NOT NULL,
            result_name TEXT NOT NULL,
            result_count INTEGER NOT NULL,
            recipe_type TEXT NOT NULL,
            ingredients_json TEXT,
            pattern_json TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_result_name ON recipes (result_name);")

    processed_files = 0
    skipped_files = []
    for file_path in recipes_path.glob("*.json"):
        with open(file_path, 'r') as f:
            data = json.load(f)

        try:
            recipe_type = data.get("type", "unknown")
            result_id, result_count = None, 1
            ingredients_flat = []
            pattern = None

            # --- Generic Parsing Logic ---
            # Get result
            if isinstance(data.get("result"), dict):
                result_data = data["result"]
                result_id = result_data.get("id") or result_data.get("item")
                result_count = result_data.get("count", 1)
            elif isinstance(data.get("result"), str):
                result_id = data["result"]

            # Handle smithing_trim and decorated_pot recipes which have no result key
            elif recipe_type in ["minecraft:smithing_trim", "minecraft:crafting_decorated_pot"]:
                # Use the filename as a proxy, as the result is dynamic
                result_id = f"minecraft:special_{file_path.stem}"
                result_count = 1

            # Handle special recipes without a fixed result (e.g., armor_dye, map_cloning)
            # We'll use the recipe's filename as a proxy for the result name.
            if not result_id and recipe_type.startswith("minecraft:crafting_special_"):
                result_id = f"minecraft:special_{file_path.stem}"
                result_count = 1  # Special recipes usually result in one item

            if not result_id:
                skipped_files.append(f"{file_path.name}: No result_id found.")
                continue  # Skip files without a valid result

            # Get ingredients from common keys
            if "ingredients" in data:  # Used in shapeless recipes
                ingredients_flat.extend(get_all_ingredient_ids(data["ingredients"]))
            if "ingredient" in data:  # Used in smelting, stonecutting
                ingredients_flat.extend(get_all_ingredient_ids(data["ingredient"]))
            if "key" in data:  # Used in shaped recipes
                # Iterate through the pattern to get the correct count of each ingredient
                if "pattern" in data:
                    for row_pattern in data["pattern"]:
                        for char in row_pattern:
                            if char != " " and char in data["key"]:
                                ingredients_flat.extend(get_all_ingredient_ids(data["key"][char]))

            # Handle smithing recipes
            if "base" in data:
                ingredients_flat.extend(get_all_ingredient_ids(data["base"]))
            # Handle recipes with an "addition" key (e.g., shulker_box_coloring)
            # This is separate from the smithing 'addition' check to handle both cases.
            # The previous check already covers smithing, this is for other types.
            if "addition" in data:
                ingredients_flat.extend(get_all_ingredient_ids(data["addition"]))
            # Handle transmute recipes (e.g., shulker_box_coloring)
            if "input" in data:
                ingredients_flat.extend(get_all_ingredient_ids(data["input"]))
            if "material" in data:
                ingredients_flat.extend(get_all_ingredient_ids(data["material"]))
            if "pattern" in data:
                pattern = data["pattern"]

            # Allow special recipes to have no ingredients defined in the file
            if not ingredients_flat and not recipe_type.startswith(
                    "minecraft:crafting_special_") and recipe_type != "minecraft:crafting_decorated_pot":
                skipped_files.append(f"{file_path.name}: No ingredients found.")
                continue  # Skip files with no ingredients found

            cur.execute(
                "INSERT INTO recipes (result_id, result_name, result_count, recipe_type, ingredients_json, pattern_json) VALUES (?, ?, ?, ?, ?, ?)",
                (result_id, get_clean_name(result_id), result_count, recipe_type,
                 json.dumps(sorted(ingredients_flat)), json.dumps(pattern) if pattern else None)
            )
            processed_files += 1

        except (KeyError, TypeError) as e:
            print(f"Warning: Could not parse {file_path.name}. Error: {e}")

    con.commit()
    con.close()
    print(f"\nDatabase '{db_path}' created/updated successfully!")
    print(f"Processed {processed_files} recipes.")
    if skipped_files:
        print(f"Skipped {len(skipped_files)} files:")
        for reason in skipped_files:
            print(f"  - {reason}")


if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    RECIPE_FOLDER = script_dir / "crafted_recipes"
    DB_FILE = script_dir / "minecraft_recipes.db"

    # print("--- Creating/Updating Database ---")
    # create_database(str(DB_FILE), RECIPE_FOLDER)
    # print("--- Database creation complete ---\n")

    print("--- Testing RecipeDB ---")
    db = RecipeDB(str(DB_FILE))
    print(f"Total recipes in database: {db.count_recipes()}")
    print("-" * 30)

    # --- Example 1: Simple name search ---
    print("▶ Example 1: Searching for recipes with 'Chest' in the name")
    chest_recipes = db.find_recipes_by_name("oak_stairs")
    if chest_recipes:
        print(f"Found {len(chest_recipes)} recipes for 'Chest':")
        for recipe in chest_recipes:
            ingredients = json.loads(recipe['ingredients_json'])
            print(f"  - {recipe['result_name']} (Type: {recipe['recipe_type']}, Ingredients: {ingredients})")
    else:
        print("No recipes found for 'Chest'.")
    print("-" * 30)

    # --- Example 2: Exact ingredient search ---
    ingredient_to_find = "minecraft:diamond"
    print(f"▶ Example 2: Searching for recipes using '{get_clean_name(ingredient_to_find)}'")
    sandstone_recipes = db.find_recipes_by_ingredient_exact(ingredient_to_find)
    if sandstone_recipes:
        print(f"Found {len(sandstone_recipes)} recipes. Showing first 5:")
        for recipe in sandstone_recipes[:5]:
            print(f"  - {recipe['result_name']}")
    else:
        print(f"No recipes found with ingredient '{ingredient_to_find}'.")
    print("-" * 30)

    # --- Example 3: Generic, multi-criteria search ---
    print("▶ Example 3: Find shaped recipes for 'Stairs' containing 'Cobblestone'")
    generic_recipes = db.find_recipes(
        name="Stairs",
        ingredients=["minecraft:cobblestone"],
        recipe_type="minecraft:crafting_shaped"
    )
    if generic_recipes:
        print(f"Found {len(generic_recipes)} matching recipe(s):")
        for recipe in generic_recipes:
            print(f"  - {recipe['result_name']}")
    else:
        print("No recipes found for the generic search.")
    print("-" * 30)

    # --- Example 4: What can I craft? (Subset match) ---
    my_inventory = ["minecraft:oak_planks"] * 8 + ["minecraft:stick"] * 4
    print(f"▶ Example 4: What can I craft with {Counter(my_inventory)}?")
    craftable = db.find_craftable_recipes(my_inventory)
    if craftable:
        print(f"Found {len(craftable)} craftable recipes. Showing first 10:")
        for recipe in craftable[:10]:
            recipe_reqs = Counter(json.loads(recipe['ingredients_json']))
            print(f"  - {recipe['result_name']} (Requires: {dict(recipe_reqs)})")
    else:
        print("Cannot craft anything with these items.")
    print("-" * 30)

    db.close()
    print("--- Test finished, connection closed ---")
