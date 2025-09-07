import os
import uuid
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from difflib import get_close_matches
from scraper import scrape_recipe  # your new scraper.py

app = Flask(__name__)

@app.template_filter('nl2br')
def nl2br_filter(s):
    if not s:
        return ''
    return s.replace('\n', '<br>')

# --- MongoDB setup ---
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["recipe_db"]
recipes_collection = db["recipes"]

# --- Helper functions ---
def load_recipes():
    return list(recipes_collection.find({}, {"_id": 0}))  # exclude MongoDB _id

def save_recipe(recipe):
    recipes_collection.insert_one(recipe)

def update_recipe(recipe_id, data):
    recipes_collection.update_one({"id": recipe_id}, {"$set": data})

def delete_recipe(recipe_id):
    recipes_collection.delete_one({"id": recipe_id})

# --- Routes ---
@app.route("/")
def index():
    recipes = load_recipes()
    filter_input = request.args.get("filters", "").lower()

    # --- Collect all attributes for autocomplete ---
    all_attrs = set()
    for r in recipes:
        for attr in r.get("attributes", []):
            all_attrs.add(attr)

    filter_attrs = []
    max_time_filter = None

    if filter_input:
        parts = [p.strip() for p in filter_input.split(",")]
        for p in parts:
            if p.startswith("<") and "min" in p:
                try:
                    max_time_filter = int(''.join(filter(str.isdigit, p)))
                except:
                    pass
            else:
                filter_attrs.append(p)

    # --- Apply fuzzy attribute filter ---
    if filter_attrs:
        def match_attributes(recipe_attrs, filter_attrs):
            recipe_attrs_lower = [a.lower() for a in recipe_attrs]
            for f in filter_attrs:
                # Use get_close_matches with cutoff=0.7 for reasonable tolerance
                matches = get_close_matches(f, recipe_attrs_lower, n=1, cutoff=0.7)
                if not matches:
                    return False
            return True

        recipes = [r for r in recipes if match_attributes(r.get("attributes", []), filter_attrs)]

    # --- Apply max time filter ---
    if max_time_filter is not None:
        def parse_time(time_str):
            try:
                return int(''.join(filter(str.isdigit, str(time_str))))
            except:
                return None
        recipes = [r for r in recipes if (t:=parse_time(r.get("time"))) is not None and t <= max_time_filter]

    # --- Sort alphabetically ---
    recipes.sort(key=lambda r: r.get("title", "").lower())
    return render_template("index.html", recipes=recipes)


@app.route("/view_recipe/<recipe_id>")
def view_recipe(recipe_id):
    recipe = recipes_collection.find_one({"id": recipe_id}, {"_id": 0})
    if not recipe:
        return "Recipe not found", 404
    return render_template("view_recipe.html", recipe=recipe)

@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        url = request.form.get("recipe_url")
        if url:
            recipe_data = scrape_recipe(url)
            if recipe_data:
                save_recipe(recipe_data)
                return redirect(url_for("index"))
            else:
                return "Failed to scrape recipe"

        # manual addition
        title = request.form.get("title")
        ingredients = request.form.get("ingredients", "").splitlines()
        instructions = request.form.get("instructions", "")
        servings = request.form.get("servings", "")
        time = request.form.get("time", "")
        attributes = request.form.get("attributes", "").splitlines()

        recipe = {
            "id": str(uuid.uuid4()),
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "servings": servings,
            "time": time,
            "attributes": attributes,
            "url": "",
        }
        save_recipe(recipe)
        return redirect(url_for("index"))

    return render_template("add_recipe.html")

@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    recipe = recipes_collection.find_one({"id": recipe_id}, {"_id": 0})
    if not recipe:
        return "Recipe not found", 404

    if request.method == "POST":
        title = request.form.get("title")
        ingredients = request.form.get("ingredients", "").splitlines()
        instructions = request.form.get("instructions", "")
        servings = request.form.get("servings", "")
        time = request.form.get("time", "")
        attributes = request.form.get("attributes", "").splitlines()

        updated_data = {
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "servings": servings,
            "time": time,
            "attributes": attributes,
        }
        update_recipe(recipe_id, updated_data)
        return redirect(url_for("view_recipe", recipe_id=recipe_id))

    return render_template("edit_recipe.html", recipe=recipe)

@app.route("/delete_recipe/<recipe_id>", methods=["POST"])
def delete(recipe_id):
    delete_recipe(recipe_id)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
