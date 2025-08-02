import json
import asyncio
from playwright.async_api import async_playwright
from utils import setup_logger

logger = setup_logger("scraper")



from urllib.parse import urljoin

from urllib.parse import urljoin
import re
import logging

logger = logging.getLogger("extract")

async def extract_offers_and_image(page, url):
    offers = []
    image = None
    desc = ""

    try:
        await page.goto(url, timeout=40000)
        await page.wait_for_timeout(5000)

        # ---- (1) Try open graph meta ----
        og_image = await page.query_selector('meta[property="og:image"]')
        if og_image:
            image = await og_image.get_attribute('content')
        # ---- (2) Try Twitter Card image ----
        if not image:
            tw_img = await page.query_selector('meta[name="twitter:image"]')
            if tw_img:
                image = await tw_img.get_attribute('content')

        # ---- (3) Look for logo/hero/main images by smart selectors ----
        prioritized_selectors = [
            'header img',               # Site header logo
            'img.logo',                 # Common logo class
            'img[alt*="logo" i]',
            'img[src*="logo"]',
            'img[alt*="main" i]',       # Sometimes main/hero image
            'img[src*="main"]',
            'img[alt*="brand" i]',
            'img[src*="brand"]',
            'img[alt*="product" i]',
            'img[src*="product"]',
            'img[alt*="academy" i]', 
            'img[src*="academy"]',
            'img[alt*="easeus" i]',
            'img[src*="easeus"]',
            'img[alt]',                 # Any image with alt
            'img',                      # Any image
        ]

        # Only take reasonable-sized real images
        def looks_valid_img(src):
            if not src: return False
            # Exclude sprites, 1x1s, tracking pixels, icons
            return not re.search(r"(sprite|icons?|favicon|1x1|pixel|blank|spacer)", src, re.I)

        if not image:
            image_found = False
            for sel in prioritized_selectors:
                elems = await page.query_selector_all(sel)
                for elem in elems:
                    src = await elem.get_attribute('src')
                    if src and looks_valid_img(src):
                        if not src.startswith("http"):
                            src = urljoin(url, src)
                        image = src
                        image_found = True
                        break
                if image_found:
                    break

        # (4) CSS background image on big visible hero div etc
        if not image:
            elems = await page.query_selector_all('[style*="background"]')
            for elem in elems:
                style = await elem.get_attribute('style')
                # Look for url("...")
                match = re.search(r'background(-image)?\s*:\s*url\([\'"]?([^)\'"]+)', style or '', re.I)
                if match:
                    css_img = match.group(2)
                    if not css_img.startswith("http"):
                        css_img = urljoin(url, css_img)
                    if looks_valid_img(css_img):
                        image = css_img
                        break

        # (5) Favicon (last-resort, usually not product!) 
        if not image:
            fav_icon = await page.query_selector('link[rel="icon"], link[rel="shortcut icon"]')
            if fav_icon:
                relimg = await fav_icon.get_attribute('href')
                if relimg and looks_valid_img(relimg):
                    image = urljoin(url, relimg)

        # ---- (6) Final fallback: the largest visible <img> on the page ----
        # (often the main product/hero image or screenshot)
        if not image:
            imgs = await page.query_selector_all('img')
            max_area = 0
            best_img = None
            for img in imgs:
                src = await img.get_attribute('src')
                # Only visible images
                box = await img.bounding_box()
                if not src or not looks_valid_img(src) or not box:
                    continue
                area = box['width'] * box['height']
                # Exclude tiny (typically icons)
                if area > max_area and area > 3000:
                    max_area = area
                    best_img = src
            if best_img:
                image = urljoin(url, best_img)

        # (7) Absolute last fallback
        if not image:
            image = "https://yourdomain.com/default-affiliate-image.png"

        # ---- Description ----
        meta_desc = await page.query_selector('meta[name="description"]')
        if meta_desc:
            desc = await meta_desc.get_attribute('content')
        else:
            first_p = await page.query_selector('p')
            if first_p:
                desc = await first_p.inner_text()

        # ---- Offer extraction ----
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





