import asyncio
import os
import json
import re
from playwright.async_api import async_playwright, Page
from amazon_vegan_scraper import handle_captcha
from ai_evaluator import evaluate_product

CATEGORY = "Consumables"
SEARCH_URL = "https://www.amazon.com/s?k=vegan+food"
OUTPUT_DIR = os.path.join("data", "products", "consumables")

PROMPT_INSTRUCTION = """
Act as an expert vegan and ethical supply chain researcher.
Evaluate the following food/consumable product's ingredients for any hidden animal derivatives (e.g., gelatin, casein, carmine, certain D3).
Cross-reference the Brand Name against known parent company food testing policies or ethical standards.
Assess supply chain labor practices based on your training data context (e.g., Fair Trade cocoa/coffee status).
"""

async def extract_product_urls(page: Page):
    await handle_captcha(page)
    try:
        await page.wait_for_selector('div[data-asin]', timeout=8000)
    except:
        return []
    links = await page.evaluate(
        '''() => {
            let urls = new Set();
            document.querySelectorAll('div[data-asin]').forEach(div => {
                let asin = div.getAttribute('data-asin');
                if (asin) {
                    let a = div.querySelector('a[href*="/dp/"]');
                    if (a && !a.href.includes("customerReviews")) urls.add(a.href);
                }
            });
            return Array.from(urls);
        }'''
    )
    return links

async def scrape_product(page: Page, url: str):
    await page.goto(url, wait_until="domcontentloaded")
    await handle_captcha(page)
    
    title = ""
    try:
        title = await page.locator('#productTitle').inner_text(timeout=8000)
    except:
        pass
        
    if not title:
        try:
            page_title = await page.title()
            if page_title:
                title = page_title.replace("Amazon.com: ", "").split(" : ")[0].strip()
        except:
            pass
        
    brand = ""
    try:
        brand_el = page.locator('#bylineInfo')
        if await brand_el.count() > 0:
            brand = await brand_el.inner_text()
            brand = brand.replace("Visit the ", "").replace(" Store", "").replace("Brand: ", "").strip()
    except:
        pass
        
    image_url = ""
    try:
        img_el = page.locator('#landingImage')
        if await img_el.count() > 0:
            image_url = await img_el.get_attribute('src')
    except:
        pass
        
    ingredients = ""
    try:
        important_info = page.locator('#important-information')
        if await important_info.count() > 0:
            ingredients = await important_info.inner_text()
        else:
            bullets = page.locator('#feature-bullets')
            if await bullets.count() > 0:
                ingredients += await bullets.inner_text()
            desc = page.locator('#productDescription')
            if await desc.count() > 0:
                ingredients += "\n" + await desc.inner_text()
    except:
        pass

    return {
        "title": title.strip(),
        "brand": brand.strip(),
        "image_url": image_url.strip(),
        "ingredients": ingredients.strip(),
        "url": url
    }

def save_hugo_markdown(product_data, ai_evaluation):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    safe_title = re.sub(r'[^a-zA-Z0-9]', '-', product_data['title'].lower())
    safe_title = re.sub(r'-+', '-', safe_title).strip('-')[:60]
    if not safe_title:
        safe_title = "product"
        
    filepath = os.path.join(OUTPUT_DIR, f"{safe_title}.md")
    
    frontmatter = f"""---
title: "{product_data['title'].replace('"', '\\"')}"
brand: "{product_data['brand'].replace('"', '\\"')}"
image: "{product_data['image_url']}"
category: "{CATEGORY}"
is_vegan: {str(ai_evaluation.get('is_vegan', False)).lower()}
company_cruelty_free: {str(ai_evaluation.get('company_cruelty_free', False)).lower()}
supply_chain_ethical: {str(ai_evaluation.get('supply_chain_ethical', False)).lower()}
amazon_url: "{product_data['url']}"
---

## Product Details

**Brand:** {product_data['brand']}

### Ingredients/Materials
{product_data['ingredients']}

## Ethical Evaluation
{ai_evaluation.get('detailed_explanation', 'No explanation provided.')}
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
    print(f"Saved {filepath}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        current_url = SEARCH_URL
        max_pages = 2
        page_num = 1
        
        while current_url and page_num <= max_pages:
            print(f"Navigating to page {page_num}: {current_url}")
            await page.goto(current_url, wait_until="domcontentloaded")
            
            product_urls = await extract_product_urls(page)
            print(f"Found {len(product_urls)} products on page {page_num}.")
            
            for url in product_urls:
                print(f"Scraping {url}")
                try:
                    data = await scrape_product(page, url)
                    if not data['title']:
                        print(f"Skipping {url} because Title was empty.")
                        continue
                        
                    print(f"Evaluating '{data['title']}' by '{data['brand']}'...")
                    metadata = {
                        "category": CATEGORY,
                        "title": data['title'],
                        "brand": data['brand'],
                        "ingredients": data['ingredients']
                    }
                    ai_eval = await evaluate_product(metadata, PROMPT_INSTRUCTION)
                    save_hugo_markdown(data, ai_eval)
                    
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"Error processing {url}: {e}")
            
            try:
                next_button = page.locator('a.s-pagination-next')
                if await next_button.count() > 0 and not await next_button.get_attribute('aria-disabled') == 'true':
                    current_url = "https://www.amazon.com" + await next_button.get_attribute('href')
                    page_num += 1
                else:
                    current_url = None
            except:
                current_url = None

        await browser.close()
        print(f"Completed scraping {CATEGORY}.")

if __name__ == "__main__":
    asyncio.run(main())
