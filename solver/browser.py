# solver/browser.py
import logging
from playwright.async_api import async_playwright

async def get_page_content_async(url: str) -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            content = await page.content()
            await browser.close()
            return content
    except Exception as e:
        logging.error(f"Failed to fetch page content for {url}: {e}")
        return None
