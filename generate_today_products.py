import json
import random
from datetime import datetime

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

def load_all_products():
    with open("software_products.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_today_products(products):
    with open("software_affiliates.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

def match_category(product, keywords):
    name = product.get("name", "").lower()
    desc = product.get("desc", "").lower()
    url = product.get("url", "").lower()
    tags = [tag.lower() for tag in product.get("tags", [])]
    combined = f"{name} {desc} {url}"
    # Check: keyword in combined fields OR keyword matches any tag
    return any(kw in combined for kw in keywords) or any(
        any(kw in tag for kw in keywords) for tag in tags
    )


def generate_today_products():
    all_products = load_all_products()
    weekday = datetime.now().weekday()
    category = WEEKDAY_CATEGORY_MAP[weekday]
    keywords = CATEGORY_KEYWORDS.get(category, [])

    if category == "mixed":
        eligible = all_products
    else:
        eligible = [p for p in all_products if match_category(p, keywords)]
        if not eligible:
            print(f"No products matched category '{category}'. Falling back to mixed.")
            eligible = all_products  # fallback to all products

    min_count, max_count = NUM_PRODUCTS_PER_DAY.get(category, NUM_PRODUCTS_PER_DAY["default"])
    selected = random.sample(eligible, min(len(eligible), random.randint(min_count, max_count)))

    save_today_products(selected)
    print(f"✅ Selected {len(selected)} '{category}' products for posting today.")


if __name__ == "__main__":
    generate_today_products()
