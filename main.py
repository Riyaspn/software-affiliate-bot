import json
import time
import requests
from datetime import datetime
from utils import setup_logger, clean_text, format_tags
from config import BOT_TOKEN, CHANNEL_ID, POST_DELAY
import re
import asyncio
from playwright.async_api import async_playwright

# ---- PART 1: Select today's products ----

from generate_today_products import generate_today_products

# Generate today's products and write to software_affiliates.json
generate_today_products()

logger = setup_logger()


# ---- PART 2: Scrape offers and images ----

OFFER_KEYWORDS = ['off', 'free', 'save', '%', 'discount', 'deal']

async def extract_offers_and_image(page, url):
    offers = []
    image = None
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(4000)  # Give time for JS offers to appear

        # Extract og:image
        og_image = await page.query_selector('meta[property="og:image"]')
        if og_image:
            image = await og_image.get_attribute('content')

        # Extract list offers
        elements = await page.query_selector_all('li, p')
        for elem in elements:
            text = await elem.inner_text()
            if any(keyword in text.lower() for keyword in OFFER_KEYWORDS):
                txt = text.strip().replace('\n', ' ')
                if 10 <= len(txt) <= 300 and txt not in offers:
                    offers.append(txt)

    except Exception as e:
        logger.error(f"❌ Error scraping {url}: {e}")
    return offers[:8], image

async def run_scraper():
    try:
        with open("software_affiliates.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("❌ software_affiliates.json not found after product selection.")
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for entry in data:
            url = entry.get("website")
            if not url:
                logger.error(f"No website for {entry.get('name', '')}")
                continue
            logger.info(f"🔍 Scraping: {entry['name']}")
            offers, image = await extract_offers_and_image(page, url)
            if offers:
                entry["offers"] = offers
            if image:
                entry["image"] = image
            logger.info(f"✅ Done: {entry['name']} | {len(offers)} offers | image: {'yes' if image else 'no'}")

        await browser.close()

    with open("software_affiliates.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("✅ Scraping and enrichment complete.")
    return data  # return enriched products


# ---- PART 3: Posting to Telegram ----

def escape_markdown(text):
    """Escapes Telegram Markdown special characters."""
    if not text:
        return ""
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def format_offers(offers):
    if not offers:
        return ""
    skip_terms = [
        'wishlist', 'offer t&cs', 'notify', 'login', 'reminder', 'events', 'stock', 'price drop'
    ]
    clean_offers = []
    for offer in offers:
        txt = escape_markdown(clean_text(offer).replace('\n', ' ').strip())
        if any(term in txt.lower() for term in skip_terms):
            continue
        if txt and len(txt) >= 10 and txt not in clean_offers:
            clean_offers.append(txt)
        if len(clean_offers) >= 3:
            break
    if not clean_offers:
        return ""
    return "\n" + "\n".join([f"• {o}" for o in clean_offers])

def send_post(product):
    name = product.get("name", "No Name")
    url = product.get("direct_affiliate_link") or product.get("affiliate_link", "")
    category = product.get("category", "Unknown")
    tags = product.get("tags", [])
    offers = product.get("offers", [])
    image_url = product.get("image")
    desc = product.get("desc", "No description available.")

    name_md = escape_markdown(clean_text(name))
    category_md = escape_markdown(clean_text(category))
    desc_md = escape_markdown(clean_text(desc))
    tags_str = format_tags(tags)
    offers_text = format_offers(offers)

    # Compose a micro-advertisement message
    message = (
        f"🔥 *{name_md}* — _{category_md}_\n"
        f"{desc_md}\n"
        f"{offers_text}\n"
        f"👉 [Grab this deal!]({url})\n"
        f"{tags_str}"
    )

    payload = {
        "chat_id": CHANNEL_ID,
        "parse_mode": "Markdown",
    }
    if image_url:
        payload["photo"] = image_url
        payload["caption"] = message
        response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json=payload)
    else:
        payload["text"] = message
        response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)

    # Logging as before
    if response.ok:
        logger.info(f"✅ Sent: {name}")
    else:
        logger.error(f"❌ Failed: {name} | Error: {response.text}")


# ---- MAIN EXECUTION ----

if __name__ == "__main__":
    logger.info("🚀 Starting unified affiliate bot: select, scrape, post.")

    # STEP 1: Today's products selected above (already writes to software_affiliates.json)

    # STEP 2: Enrich with offers/images
    actloop = asyncio.get_event_loop()
    enriched_products = actloop.run_until_complete(run_scraper())
    if not enriched_products:
        logger.error("No products found after enrichment, exiting.")
        exit(1)

    # STEP 3: Post
    for product in enriched_products:
        send_post(product)
        time.sleep(POST_DELAY)
