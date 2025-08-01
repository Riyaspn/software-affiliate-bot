import json
import asyncio
from playwright.async_api import async_playwright
from utils import setup_logger

logger = setup_logger("scraper")


async def extract_offers_and_image(page, url):
    offers = []
    image = None
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(4000)  # Slightly longer wait for load

        # Extract og:image
        og_image = await page.query_selector('meta[property="og:image"]')
        if og_image:
            image = await og_image.get_attribute('content')
        # Fallback 1: Try standard <img> in header or main
        if not image:
            img_tag = await page.query_selector('header img') or await page.query_selector('img')
            if img_tag:
                src = await img_tag.get_attribute('src')
                # If src is relative, join with base URL
                if src and not src.startswith("http"):
                    from urllib.parse import urljoin
                    image = urljoin(url, src)
                else:
                    image = src


        # Extract visible offer points (basic)
        elements = await page.query_selector_all('li, p')
        for elem in elements:
            text = await elem.inner_text()
            if any(keyword in text.lower() for keyword in ['off', 'free', 'save', '%', 'discount', 'deal']):
                text = text.strip()
                if 10 <= len(text) <= 300 and text not in offers:
                    offers.append(text)

    except Exception as e:
        logger.error(f"❌ Error scraping {url}: {e}")
    return offers[:8], image


async def main():
    with open("software_affiliates.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for entry in data:
            url = entry.get("website")  # <-- Use correct key here
            if not url:
                logger.error(f"❌ No website URL for {entry.get('name', 'unknown')}, skipping.")
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
    logger.info("✅ Updated software_affiliates.json with offers and images.")


if __name__ == "__main__":
    asyncio.run(main())

