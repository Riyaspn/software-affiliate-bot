import json
import asyncio
from playwright.async_api import async_playwright
from utils import setup_logger

logger = setup_logger("scraper")



from urllib.parse import urljoin
import re
import logging

logger = logging.getLogger("extract")



from urllib.parse import urlparse, urljoin
import re
import logging

logger = logging.getLogger("extract")

async def extract_offers_and_image(page, url):
    offers = []
    image = None
    desc = ""

    def looks_valid_img(src):
        if not src or src.strip() == "":
            return False
        # Exclude sprites, icons, favicons, 1x1, pixels, blanks, spacers
        return not re.search(r"(sprite|icon|favicon|1x1|pixel|blank|spacer)", src, re.I)

    try:
        await page.goto(url, timeout=40000)
        await page.wait_for_timeout(5000)  # JS-render

        # (1) Open Graph
        og_image = await page.query_selector('meta[property="og:image"]')
        if og_image:
            image = await og_image.get_attribute('content')

        # (2) Twitter Card
        if not image:
            tw_img = await page.query_selector('meta[name="twitter:image"]')
            if tw_img:
                image = await tw_img.get_attribute('content')

        # (3) <img> in header/nav or first N images (SVG/PNG/JPG/WebP ok, even size=0)
        if not image:
            header_imgs = await page.query_selector_all('header img, nav img')
            checked_imgs = header_imgs or await page.query_selector_all('img')
            for img in checked_imgs[:8]:
                src = await img.get_attribute('src')
                if src:
                    if not src.startswith('http'):
                        src = urljoin(url, src)
                    if looks_valid_img(src) and any(src.lower().endswith(x) for x in ('.svg', '.png', '.jpg', '.jpeg', '.webp')):
                        image = src
                        break

        # (4) Smart selectors for common product/brand/hero image patterns
        prioritized_selectors = [
            'img.logo',
            'img[alt*="logo" i]',
            'img[src*="logo"]',
            'img[alt*="brand" i]',
            'img[src*="brand"]',
            'img[alt*="main" i]',
            'img[src*="main"]',
            'img[alt*="product" i]',
            'img[src*="product"]',
            'img[alt*="trusted" i]',
            'img[src*="trusted"]',
            'img[alt*="laplink" i]',
            'img[src*="laplink"]',
        ]
        if not image:
            for sel in prioritized_selectors:
                elems = await page.query_selector_all(sel)
                for elem in elems:
                    src = await elem.get_attribute('src')
                    if src and looks_valid_img(src):
                        if not src.startswith("http"):
                            src = urljoin(url, src)
                        image = src
                        break
                if image:
                    break

        # (5) CSS background-image from inline style
        if not image:
            elems = await page.query_selector_all('[style*="background"]')
            for elem in elems:
                style = await elem.get_attribute('style')
                match = re.search(r'background(-image)?\s*:\s*url\([\'"]?([^)\'"]+)', style or '', re.I)
                if match:
                    css_img = match.group(2)
                    if not css_img.startswith("http"):
                        css_img = urljoin(url, css_img)
                    if looks_valid_img(css_img):
                        image = css_img
                        break

        # (6) Favicon as fallback
        if not image:
            fav_icon = await page.query_selector('link[rel="icon"], link[rel="shortcut icon"]')
            if fav_icon:
                relimg = await fav_icon.get_attribute('href')
                if relimg:
                    relimg = urljoin(url, relimg)
                    if looks_valid_img(relimg):
                        image = relimg

        # (7) Largest visible <img> as last content fallback
        if not image:
            imgs = await page.query_selector_all('img')
            max_area = 0
            best_img = None
            for img in imgs:
                src = await img.get_attribute('src')
                box = await img.bounding_box()
                if not src or not looks_valid_img(src) or not box:
                    continue
                area = (box['width'] or 1) * (box['height'] or 1)
                if area > max_area and area > 2500:
                    max_area = area
                    best_img = src
            if best_img:
                if not best_img.startswith('http'):
                    best_img = urljoin(url, best_img)
                image = best_img

        # (8) ABSOLUTE DYNAMIC FALLBACK: use domain for avatar/fallback
        if not image:
            domain = urlparse(url).netloc.replace("www.", "")
            # Option A: ui-avatars (text initials, colored bg)
            image = f"https://ui-avatars.com/api/?name={domain}&background=random"
            # Option B: DiceBear Avatar SVG (more visual, unique by domain)
            # image = f"https://api.dicebear.com/7.x/identicon/svg?seed={domain}"
            # Option C: Google favicon as last resort
            # image = f"https://www.google.com/s2/favicons?sz=128&domain={domain}"

        # --- Description extraction ---
        meta_desc = await page.query_selector('meta[name="description"]')
        if meta_desc:
            desc = await meta_desc.get_attribute('content')
        else:
            first_p = await page.query_selector('p')
            if first_p:
                desc = await first_p.inner_text()

        # --- Offer extraction ---
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






