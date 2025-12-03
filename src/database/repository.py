import sqlite3
import json
from collections import Counter
from typing import List, Dict, Any, Optional

class RecipeDB:
    def __init__(self, db_path: str):
        """Initializes the database connection."""
        self.db_path = db_path
        # Allow connection to be used from different threads for pytest
        self.con = sqlite3.connect(db_path, check_same_thread=False)
        self.con.row_factory = sqlite3.Row

    def find_recipes_by_id(self, item_id: str) -> List[Dict[str, Any]]:
        """Finds recipes where the result ID matches the given ID."""
        if not item_id.startswith("minecraft:"):
            item_id = f"minecraft:{item_id}"

        cur = self.con.cursor()
        cur.execute("SELECT * FROM recipes WHERE result_id = ?", (item_id,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def find_recipes_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Finds recipes where the result name contains the given name."""
        cur = self.con.cursor()
        cur.execute("SELECT * FROM recipes WHERE result_name LIKE ?", (f"%{name}%",))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def find_recipes_by_ingredient_exact(self, ingredient_id: str) -> List[Dict[str, Any]]:
        """
        Finds recipes that contain a specific ingredient by its exact ID,
        using SQLite's JSON functions for precision.
        """
        cur = self.con.cursor()
        # This query joins the recipes table with a temporary table generated
        # from the JSON array of ingredients, allowing for an exact match.
        query = """
            SELECT DISTINCT r.* FROM recipes r, json_each(r.ingredients_json) j
            WHERE j.value = ?
        """
        cur.execute(query, (ingredient_id,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def find_craftable_recipes(self, available_ingredients: List[str], exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        Finds recipes that can be crafted with a given set of ingredients.

        :param available_ingredients: A list of item IDs available for crafting.
        :param exact_match: If True, the recipe must use exactly the ingredients provided.
                            If False (default), the recipe can use a subset of the provided ingredients.
        :return: A list of matching recipe dictionaries.
        """

        cur = self.con.cursor()
        cur.execute("SELECT * FROM recipes WHERE ingredients_json IS NOT NULL AND ingredients_json != '[]'")
        all_recipes = cur.fetchall()

        craftable_recipes = []
        # Use a Counter for efficient counting of available ingredients
        available_counts = Counter(available_ingredients)

        for row in all_recipes:
            recipe_ingredient_list = json.loads(row['ingredients_json'])
            if not recipe_ingredient_list:  # Skip recipes with no ingredients
                continue

            recipe_counts = Counter(recipe_ingredient_list)

            if exact_match:
                # For an exact match, the ingredients must be identical
                if recipe_counts == available_counts:
                    craftable_recipes.append(dict(row))
            else:  # Subset match (check if available ingredients can satisfy the recipe)
                # Check if we have enough of each required ingredient
                can_craft = True
                for ing, count in recipe_counts.items():
                    if ing.startswith('#'): # Handle tags (e.g., #minecraft:planks)
                        # Simplification: Check if we have enough of ANY item that could match the tag's name.
                        # e.g., for '#minecraft:planks', check all items with 'planks' in their name.
                        tag_name = ing.split(':')[-1]
                        available_tag_items_count = sum(
                            available_counts[item] for item in available_counts if tag_name in item
                        )
                        if available_tag_items_count < count:
                            can_craft = False
                            break
                    elif available_counts[ing] < count:
                        # Not enough of a specific ingredient
                        can_craft = False
                        break
                if can_craft:
                    craftable_recipes.append(dict(row))

        return craftable_recipes

    def find_recipes(self, name: Optional[str] = None, ingredients: Optional[List[str]] = None,
                     recipe_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Generic search for recipes with multiple optional criteria."""
        query_parts = ["SELECT * FROM recipes WHERE 1=1"]
        params = []

        if name:
            query_parts.append("AND result_name LIKE ?")
            params.append(f"%{name}%")
        if ingredients:
            for ingredient in ingredients:
                query_parts.append("AND ingredients_json LIKE ?")
                params.append(f'%"{ingredient}"%') # Simple but effective for "AND"
        if recipe_type:
            query_parts.append("AND recipe_type = ?")
            params.append(recipe_type)

        query_parts.append("LIMIT ?")
        params.append(limit)

        query = " ".join(query_parts)
        cur = self.con.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def count_recipes(self):
        """Counts the total number of recipes in the database."""
        cur = self.con.cursor()
        cur.execute("SELECT COUNT(*) FROM recipes")
        return cur.fetchone()[0]

    def close(self):
        """Closes the database connection if it is open."""
        if self.con:
            self.con.close()
            self.con = None

    def __del__(self):
        """Destructor to ensure the connection is closed when the object is deleted."""
        self.close()