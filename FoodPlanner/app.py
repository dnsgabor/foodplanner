
from flask import Flask, render_template, request, redirect, url_for
import os, json
from scraper import scrape_recipe   # <-- import scraper here
import uuid


app = Flask(__name__)
DEBUG_SCRAPER = True  # Set to False in production


def load_recipes():
    file_path = os.path.join(os.path.dirname(__file__), "recipes.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            recipes = json.load(f)
        # --- migrate missing fields ---
        for r in recipes:
            if "id" not in r: r["id"] = str(uuid.uuid4())
            if "attributes" not in r: r["attributes"] = []
            if "url" not in r: r["url"] = ""
        # save back if we changed anything
        save_recipes(recipes)
        return recipes
    else:
         # Default recipes to populate the file if it doesn't exist
        default_recipes = [
            {
                "id": str(uuid.uuid4()),
                "title": "Spaghetti Bolognese",
                "ingredients": ["spaghetti", "minced beef", "tomato sauce", "onion"],
                "instructions": "Cook the spaghetti and mix with sauce.",
                "attributes": [],
                "url": ""
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Pancakes",
                "ingredients": ["flour", "milk", "eggs", "butter", "baking powder"],
                "instructions": "Mix ingredients and cook in a pan.",
                "attributes": ["dessert", "easy"],
                "url": ""
            }
        ]
        # Save the default recipes to 'recipes.json'
        with open("recipes.json", "w") as f:
            json.dump(default_recipes, f, indent=4)
        return default_recipes  # Return the default recipes for display


def save_recipes(recipes):
    file_path = os.path.join(os.path.dirname(__file__), "recipes.json")
    with open(file_path, "w") as f:
        json.dump(recipes, f, indent=4)


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        # Check if it's a URL submission or manual form submission
        recipe_url = request.form.get("recipe_url")
        if recipe_url:
            # Scrape the recipe from the URL
            recipe_data = scrape_recipe(recipe_url)
            if recipe_data:
                # Load existing recipes
                recipes = load_recipes()
                # Add the new recipe
                recipes.append(recipe_data)
                # Save the updated list back to the JSON file
                save_recipes(recipes)
                return redirect(url_for("index"))
            else:
                return "Failed to scrape the recipe, please try again."

        # Manual recipe addition
        title = request.form["title"]
        ingredients = request.form["ingredients"].splitlines()
        instructions = request.form["instructions"]
        # Process attributes (comma separated)
        attributes_raw = request.form.get("attributes", "")
        attributes = [a.strip() for a in attributes_raw.split(",") if a.strip()]

        new_recipe = {
            "id": str(uuid.uuid4()),
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "attributes": attributes,
            "url": ""
        }

        # Load existing recipes
        recipes = load_recipes()
        # Add the new recipe
        recipes.append(new_recipe)
        # Save the updated list back to the JSON file
        save_recipes(recipes)

        return redirect(url_for("index"))

    return render_template("add_recipe.html")

@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    recipes = load_recipes()
    recipe = next((r for r in recipes if r["id"] == recipe_id), None)
    if not recipe:
        return "Recipe not found", 404

    if request.method == "POST":
        recipe["title"] = request.form["title"]
        recipe["ingredients"] = request.form["ingredients"].splitlines()
        recipe["instructions"] = request.form["instructions"]
        attributes_raw = request.form.get("attributes", "")
        recipe["attributes"] = [a.strip() for a in attributes_raw.split(",") if a.strip()]

        save_recipes(recipes)
        return redirect(url_for("view_recipe", recipe_id=recipe_id))

    return render_template("edit_recipe.html", recipe=recipe)

@app.route("/delete_recipe/<recipe_id>", methods=["POST"])
def delete_recipe(recipe_id):
    recipes = load_recipes()
    new_recipes = [r for r in recipes if r["id"] != recipe_id]
    if len(new_recipes) == len(recipes):
        return "Recipe not found", 404

    save_recipes(new_recipes)
    return redirect(url_for("index"))


@app.route("/")
def index():
    recipes = load_recipes()
    recipes = sorted(recipes, key=lambda r: r["title"].lower())

    # Optional attribute filter
    attribute = request.args.get("attribute")
    if attribute:
        recipes = [r for r in recipes if attribute.lower() in [a.lower() for a in r.get("attributes", [])]]

    return render_template("index.html", recipes=recipes, attribute=attribute)


@app.route("/view_recipe/<recipe_id>")
def view_recipe(recipe_id):
    recipes = load_recipes()
    recipe = next((r for r in recipes if r["id"] == recipe_id), None)
    if not recipe:
        return "Recipe not found", 404
    return render_template("view_recipe.html", recipe=recipe)

if __name__ == "__main__":
    app.run(debug=True)