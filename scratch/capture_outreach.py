import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("Navigating to http://localhost:8000...")
        await page.goto("http://localhost:8000")
        
        # Wait for the status grid to load and render cards
        await page.wait_for_timeout(4000)
        
        # Take screenshot of the outreach tab
        screenshot_path = os.path.abspath("outreach_tracker_screenshot.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to: {screenshot_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
