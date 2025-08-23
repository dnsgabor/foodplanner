import uuid
import json
import requests
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me
from recipe_scrapers._exceptions import WebsiteNotImplementedError

DEBUG_SCRAPER = False


def scrape_recipe(url: str):
    """
    Hybrid recipe scraper:
    1. Try recipe-scrapers (works for many popular sites).
    2. Fallback to JSON-LD + heuristics with BeautifulSoup.
    """

    # --- Try recipe-scrapers first ---
    try:
        scraper = scrape_me(url)
        return {
            "id": str(uuid.uuid4()),
            "title": scraper.title(),
            "ingredients": scraper.ingredients(),
            "instructions": scraper.instructions(),
            "attributes": [],
            "url": url,
        }
    except WebsiteNotImplementedError:
        if DEBUG_SCRAPER:
            print(f"[DEBUG] Site not supported by recipe-scrapers, falling back: {url}")
    except Exception as e:
        if DEBUG_SCRAPER:
            print(f"[DEBUG] recipe-scrapers error for {url}: {e}")

    # --- Fallback: JSON-LD / heuristics ---
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            if DEBUG_SCRAPER:
                print(f"[DEBUG] HTTP {response.status_code} fetching {url}")
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        best_data = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for d in data:
                        if isinstance(d, dict) and "Recipe" in str(d.get("@type")):
                            if "recipeIngredient" in d:
                                best_data = d
                                break
                elif isinstance(data, dict) and "Recipe" in str(data.get("@type", "")):
                    if "recipeIngredient" in data:
                        best_data = data
                        break
            except Exception:
                continue

        if best_data:
            title = best_data.get("name", "")
            if not title or "swissmilk" in title.lower():
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else "Untitled Recipe"

            ingredients = best_data.get("recipeIngredient", [])
            raw_instructions = best_data.get("recipeInstructions", [])
            steps = []
            if isinstance(raw_instructions, list):
                for step in raw_instructions:
                    if isinstance(step, dict):
                        steps.append(step.get("text", ""))
                    else:
                        steps.append(str(step))
            elif isinstance(raw_instructions, str):
                steps = [raw_instructions]

            return {
                "id": str(uuid.uuid4()),
                "title": title,
                "ingredients": ingredients,
                "instructions": "\n".join(s for s in steps if s.strip()),
                "attributes": [],
                "url": url,
            }

        # Last-resort fallback
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else url
        ingredients = [li.get_text(strip=True) for li in soup.find_all("li")]
        instructions = "\n".join(p.get_text(strip=True) for p in soup.find_all("p"))

        return {
            "id": str(uuid.uuid4()),
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions or "No instructions found",
            "attributes": [],
            "url": url,
        }

    except Exception as e:
        if DEBUG_SCRAPER:
            print(f"[DEBUG] Heuristic scraper error: {e}")
        return None
