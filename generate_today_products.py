import json
import random
from datetime import datetime
import os

# Map weekdays to themes/categories
WEEKDAY_CATEGORY_MAP = {
    0: "productivity",  # Monday
    1: "learning",      # Tuesday
    2: "finance",       # Wednesday
    3: "hosting",       # Thursday
    4: "creativity",    # Friday
    5: "travel",        # Saturday
    6: "mixed"          # Sunday
}

CATEGORY_KEYWORDS = {
    "productivity": ["productivity", "work", "team"],
    "learning": ["learning", "academy", "education", "tools"],
    "finance": ["finance", "invoice", "account", "budget"],
    "hosting": ["hosting", "vpn", "server", "cloud"],
    "creativity": ["creative", "media", "design", "edit", "photo", "camera", "graphics", "art", "video", "image"],
    "travel": ["travel", "booking", "roaming"],
    "mixed": []  # use everything
}

NUM_PRODUCTS_PER_DAY = {
    "default": (3, 5),
    "mixed": (5, 8)
}

PRODUCTS_FILE = "software_products.json"
HISTORY_FILE = "post_history.json"
OUTPUT_FILE = "software_affiliates.json"

def load_all_products():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_today_products(products):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

def load_history(month_key):
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = {}
    posted_names = set(history.get(month_key, []))
    return history, posted_names

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def match_category(product, keywords):
    name = product.get("name", "").lower()
    desc = product.get("desc", "").lower()
    website = product.get("website", "").lower()  # fix: change from 'url' (your products use 'website')
    tags = [tag.lower() for tag in product.get("tags", [])]
    combined = f"{name} {desc} {website}"
    # keyword substring in name/desc/website OR in any tag
    return any(kw in combined for kw in keywords) or any(
        any(kw in tag for kw in keywords) for tag in tags
    )

def generate_today_products():
    all_products = load_all_products()
    weekday = datetime.now().weekday()
    category = WEEKDAY_CATEGORY_MAP[weekday]
    keywords = CATEGORY_KEYWORDS.get(category, [])
    month_key = datetime.now().strftime("%Y-%m")

    history, posted_names = load_history(month_key)

    # 1. Filter per category (and not posted yet this month)
    if category == "mixed":
        eligible = [p for p in all_products if p["name"] not in posted_names]
    else:
        eligible = [p for p in all_products if match_category(p, keywords) and p["name"] not in posted_names]
        if not eligible:
            print(f"No products matched category '{category}' or all already posted this month. Falling back to mixed.")
            eligible = [p for p in all_products if p["name"] not in posted_names]

    # 2. If STILL none left, reset month's history (begin new rotation), select from all/category as usual:
    if not eligible:
        posted_names = set()
        if category == "mixed":
            eligible = all_products
        else:
            eligible = [p for p in all_products if match_category(p, keywords)]
            if not eligible:  # fallback again to all
                eligible = all_products

    min_count, max_count = NUM_PRODUCTS_PER_DAY.get(category, NUM_PRODUCTS_PER_DAY["default"])
    todays_count = min(len(eligible), random.randint(min_count, max_count))
    selected = random.sample(eligible, todays_count)

    save_today_products(selected)
    print(f"✅ Selected {len(selected)} '{category}' products for posting today.")

    # 3. Update and save the posted history
    posted_today = {p["name"] for p in selected}
    history[month_key] = list(posted_names | posted_today)
    save_history(history)

if __name__ == "__main__":
    generate_today_products()
