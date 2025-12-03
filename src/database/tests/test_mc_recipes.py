import pytest
import os
import json
from pathlib import Path
from ..builder import create_database
from ..repository import RecipeDB

# Defines a test database name used only for tests
TEST_DB_NAME = "test_recipes.db"


@pytest.fixture(scope="module")
def db_connection():
    """
    Pytest Fixture: Creates a test database for the entire test session.
    - `scope="module"` ensures the database is created only once for all tests in this module.
    - `yield` returns control to the tests and executes the code afterward to clean up.
    """
    # Determine paths relative to the test file
    script_dir = Path(__file__).parent
    recipe_folder = script_dir / "crafted_recipes"
    db_path = script_dir / TEST_DB_NAME

    # Ensure recipe files are present
    assert recipe_folder.exists(), "The 'crafted_recipes' folder was not found. Please ensure it exists."
    assert any(recipe_folder.glob("*.json")), "No JSON recipe files found in the 'crafted_recipes' folder."

    # Create the database
    create_database(str(db_path), recipe_folder)

    # Create and provide a RecipeDB instance for the tests
    db = RecipeDB(str(db_path))
    yield db

    # Clean up: close the connection and delete the test database file
    db.close()
    os.remove(db_path)


def test_database_creation_and_count(db_connection):
    """Tests if the database is created and contains the expected number of recipes."""
    # The total number of JSON files is 1461
    expected_recipe_count = 1461
    assert db_connection.count_recipes() == expected_recipe_count


@pytest.mark.parametrize("name, expected_id, should_find", [
    ("Crafting Table", "minecraft:crafting_table", True),  # Exact match
    ("chest", "minecraft:chest", True),  # Partial, case-insensitive
    ("NonExistentItem", None, False),  # Should not be found
])
def test_find_recipes_by_name(db_connection, name, expected_id, should_find):
    """Tests finding recipes by full or partial name."""
    recipes = db_connection.find_recipes_by_name(name)
    if should_find:
        assert len(recipes) > 0
        # Check if the expected item is in the results
        assert any(r["result_id"] == expected_id for r in recipes)
    else:
        assert len(recipes) == 0


@pytest.mark.parametrize("ingredient, expected_result, should_find", [
    ("minecraft:stick", "Torch", True),  # Common ingredient
    ("minecraft:diamond", "Diamond Block", True),  # Valuable ingredient used directly
    ("minecraft:unobtainium_ingot", None, False),  # Non-existent ingredient
])
def test_find_recipes_by_ingredient_exact(db_connection, ingredient, expected_result, should_find):
    """Tests finding recipes by an exact ingredient ID."""
    recipes = db_connection.find_recipes_by_ingredient_exact(ingredient)
    if should_find:
        assert len(recipes) > 0
        result_names = [r["result_name"] for r in recipes]
        assert expected_result in result_names
    else:
        assert len(recipes) == 0


def test_find_craftable_recipes_subset(db_connection):
    """Tests finding all recipes craftable from a given set of ingredients (subset match)."""
    inventory = ["minecraft:oak_planks"] * 8 + ["minecraft:stick"] * 7
    recipes = db_connection.find_craftable_recipes(inventory)
    assert len(recipes) > 0
    result_names = [r["result_name"] for r in recipes]
    # Things you can make with planks and sticks
    assert "Oak Sign" in result_names
    assert "Oak Fence" in result_names
    assert "Ladder" in result_names  # Needs 7 sticks
    assert "Chest" in result_names  # Needs 8 planks
    assert "Crafting Table" in result_names  # Needs 4 planks


def test_find_craftable_recipes_exact(db_connection):
    """Tests finding a recipe that requires an exact set of ingredients."""
    # A lever requires exactly one stick and one cobblestone
    inventory = ["minecraft:stick", "minecraft:cobblestone"]
    recipes = db_connection.find_craftable_recipes(inventory, exact_match=True)

    assert len(recipes) > 0
    assert any(r["result_name"] == "Lever" for r in recipes)


def test_find_craftable_recipes_insufficient_ingredients(db_connection):
    """Tests that a recipe is not returned if ingredients are insufficient."""
    inventory = ["minecraft:oak_planks"] * 3  # Crafting table needs 4
    recipes = db_connection.find_craftable_recipes(inventory)
    result_names = [r["result_name"] for r in recipes]
    assert "Crafting Table" not in result_names


def test_find_recipes_generic_search(db_connection):
    """Tests the generic find_recipes method with multiple criteria."""
    # Find all shaped recipes for "Stairs" that use "Cobblestone"
    recipes = db_connection.find_recipes(
        name="Stairs",
        ingredients=["minecraft:cobblestone"],
        recipe_type="minecraft:crafting_shaped"
    )
    assert len(recipes) > 0
    cobblestone_stairs_recipe = next((r for r in recipes if r["result_id"] == "minecraft:cobblestone_stairs"), None)
    assert cobblestone_stairs_recipe is not None
    assert "Cobblestone" in cobblestone_stairs_recipe["result_name"]
    assert "minecraft:cobblestone" in json.loads(cobblestone_stairs_recipe["ingredients_json"])


def test_special_recipes_are_included(db_connection):
    """Tests that special recipes (e.g., with no fixed ingredients) are in the database."""
    # armor_dye has no ingredients in its JSON file
    recipes = db_connection.find_recipes_by_name("Special Armor Dye")
    assert len(recipes) == 1
    recipe = recipes[0]
    assert recipe["result_id"] == "minecraft:special_armor_dye"
    assert recipe["recipe_type"] == "minecraft:crafting_special_armordye"
    assert json.loads(recipe["ingredients_json"]) == []


def test_database_integrity_on_shaped_recipe(db_connection):
    """Performs a spot check on a shaped recipe (Chest) to ensure all data is correct."""
    recipes = db_connection.find_recipes_by_name("Chest")
    chest_recipe = next((r for r in recipes if r["result_id"] == "minecraft:chest"), None)

    assert chest_recipe is not None
    assert chest_recipe["result_count"] == 1
    assert chest_recipe["recipe_type"] == "minecraft:crafting_shaped"

    ingredients = json.loads(chest_recipe["ingredients_json"])
    pattern = json.loads(chest_recipe["pattern_json"])

    # A chest is 8 planks
    assert isinstance(ingredients, list)
    assert len(ingredients) == 8
    assert all(ing == "#minecraft:planks" for ing in ingredients)

    # Check the pattern
    assert pattern == ["###", "# #", "###"]
