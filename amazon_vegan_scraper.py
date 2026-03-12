import asyncio
from playwright.async_api import async_playwright, Page
import winsound
import sys

async def handle_captcha(page: Page):
    """
    Sophisticated interceptor checks the page title and URL for Amazon CAPTCHA
    or bot-detection challenge. Pauses execution, plays an alert sound,
    and loops indefinitely until the user solves it and resumes.
    """
    try:
        await page.wait_for_load_state("load", timeout=3000)
    except:
        pass
        
    title = await page.title()
    url = page.url
    
    try:
        content = await page.content()
    except:
        content = ""
    
    captcha_indicators = ["captcha", "bot", "sorry!"]
    
    is_captcha = "errors/validatecaptcha" in url.lower() or \
                 any(indicator in title.lower() for indicator in captcha_indicators) or \
                 "Type the characters you see in this image" in content or \
                 "Sorry! Something went wrong!" in content
                 
    if is_captcha:
        print("\n" + "="*60)
        print("🚨 AMAZON CAPTCHA OR BOT DETECTION DETECTED 🚨")
        print("="*60)
        print("Target URL:", url)
        print("Please manually solve the CAPTCHA in the visible Chrome window.")
        
        # Play alert sound
        for _ in range(3):
            winsound.Beep(1000, 500)
            await asyncio.sleep(0.5)
            
        print("\n>>> Press 'Enter' in this terminal ONLY AFTER you have solved it to resume... <<<")
        
        # Wait indefinitely for user to press Enter
        await asyncio.to_thread(input)
        
        print("\nResuming execution... Double checking if CAPTCHA is cleared.")
        # Re-check recursively if they didn't actually solve it
        await asyncio.sleep(2)
        await handle_captcha(page)

async def main():
    print("Starting Amazon Vegan Scraper...")
    async with async_playwright() as p:
        # Launch a visible, non-headless Google Chrome instance
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome"
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Example navigation
        test_url = "https://www.amazon.com/errors/validateCaptcha"
        print(f"Navigating to {test_url} for CAPTCHA testing...")
        
        try:
            await page.goto(test_url, wait_until="domcontentloaded")
            await handle_captcha(page)
            
            print("Successfully passed CAPTCHA interceptor.")
            # Continue with main scraping logic here...
            
        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            await browser.close()
            print("Browser closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript terminated by user.")
        sys.exit(0)
