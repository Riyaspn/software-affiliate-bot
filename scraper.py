import json
import asyncio
from playwright.async_api import async_playwright
from utils import setup_logger

logger = setup_logger("scraper")


from urllib.parse import urljoin

async def extract_offers_and_image(page, url):
    offers = []
    image = None
    desc = ""
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(4000)

        # 1. Try OG image first
        og_image = await page.query_selector('meta[property="og:image"]')
        if og_image:
            image = await og_image.get_attribute('content')

        # 2. Fallback: find logo image by typical header/img/logo selectors
        if not image:
            selectors = [
                'header img',            # common header logo
                'img.logo',              # class="logo"
                'img[alt*="logo"]',      # alt containing 'logo'
                'img[src*="logo"]',      # src containing 'logo'
                'img[alt*="easeus"]',    # alt containing EaseUS
                'img[src*="easeus"]',    # src containing EaseUS
                'link[rel="icon"]',      # favicon
                'link[rel="shortcut icon"]'
            ]
            for sel in selectors:
                elem = await page.query_selector(sel)
                if elem:
                    if sel.startswith('img'):
                        src = await elem.get_attribute('src')
                    else:
                        src = await elem.get_attribute('href')
                    if src:
                        # Fix relative URLs
                        if not src.startswith("http"):
                            src = urljoin(url, src)
                        image = src
                        break  # stop at first found

        # 3. Still nothing? Fallback to favicon (always present)
        if not image:
            favicon = await page.query_selector('link[rel="icon"]')
            if favicon:
                src = await favicon.get_attribute('href')
                if src:
                    image = urljoin(url, src)

        # Extract meta description for blurb, and any offers as before...
        meta_desc = await page.query_selector('meta[name="description"]')
        if meta_desc:
            desc = await meta_desc.get_attribute('content')
        else:
            first_p = await page.query_selector('p')
            if first_p:
                desc = await first_p.inner_text()

        elements = await page.query_selector_all('li, p')
        for elem in elements:
            text = await elem.inner_text()
            if any(keyword in text.lower() for keyword in ['off', 'free', 'save', '%', 'discount', 'deal']):
                txt = text.strip().replace('\n', ' ')
                if 10 <= len(txt) <= 300 and txt not in offers:
                    offers.append(txt)

    except Exception as e:
        logger.error(f"❌ Error scraping {url}: {e}")
    return offers[:8], image, desc



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


