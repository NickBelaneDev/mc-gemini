import json
from pathlib import Path
from typing import List, Dict, Optional, Any

RECIPE_DIR = Path("crafted_recipes")


def find_recipes_by_filename(search_term: str) -> List[Dict[str, Any]]:
    """
    Sucht Rezepte, deren Dateiname den Suchbegriff enthält.
    Liest die passenden JSON-Dateien und gibt deren Inhalt zurück.
    """
    results = []
    if not RECIPE_DIR.is_dir():
        print(f"Fehler: Rezept-Ordner '{RECIPE_DIR}' nicht gefunden.")
        return results

    for file_path in RECIPE_DIR.glob("*.json"):
        filename = file_path.name
        if search_term in filename:
            # Deine heuristische Regel, um z.B. "stone_from_stone_bricks" auszuschließen
            if "from" in filename and filename.find("from") < filename.find(search_term):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Füge den Dateinamen für die spätere Auswahl hinzu
                    data["_source_filename"] = filename
                    results.append(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Konnte Datei {filename} nicht lesen: {e}")

    return results


def get_recipe_names(recipes: List[Dict[str, Any]]) -> List[str]:
    """Extrahiert die Dateinamen aus einer Liste von Rezept-Daten."""
    return [recipe.get("_source_filename", "unbekannt.json") for recipe in recipes]


def get_final_recipe(recipes: List[Dict[str, Any]], filename: str) -> Optional[Dict[str, Any]]:
    """Findet das vollständige Rezept-Wörterbuch anhand seines Dateinamens in der vorab geladenen Liste."""
    for recipe in recipes:
        if recipe.get("_source_filename") == filename:
            return recipe
    return None


if __name__ == "__main__":
    # Simulieren des mehrstufigen Prozesses
    # 1. LLM extrahiert 'stone_bricks' aus der User-Frage
    search_query = "stone_bricks"
    found_recipes = find_recipes_by_filename(search_query)
    
    # 2. Wir geben dem LLM eine Liste von Kandidaten
    candidate_names = get_recipe_names(found_recipes)
    print(f"Gefundene Kandidaten für '{search_query}': {candidate_names}")

    # 3. LLM wählt den besten Kandidaten aus (hier simulieren wir die Wahl)
    chosen_filename = "stone_bricks.json" # Simuliert die "intelligente" Wahl des LLM
    print(f"\nLLM hat gewählt: {chosen_filename}")

    # 4. Wir holen uns das vollständige Rezept, um es dem LLM für die finale Antwort zu geben
    final_recipe_data = get_final_recipe(found_recipes, chosen_filename)

    if final_recipe_data:
        print(f"\nFinale Rezeptdaten für die Antwortgenerierung:\n{json.dumps(final_recipe_data, indent=2)}")
    else:
        print(f"Fehler: Das gewählte Rezept '{chosen_filename}' konnte nicht in den Ergebnissen gefunden werden.")
