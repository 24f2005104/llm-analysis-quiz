import time
import httpx
import asyncio
from playwright.async_api import async_playwright
from .config import EMAIL, SECRET, DEFAULT_SUBMIT_URL, MAX_BROWSER_CHARS, SUBMIT_RETRIES, SUBMIT_RETRY_DELAY
from .logger import logger

CURRENT_URL = None

async def browse(url: str):
    global CURRENT_URL
    CURRENT_URL = url

    logger.info(f"Browsing URL | url={url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        text = await page.inner_text("body")
        await browser.close()

    logger.info("Page rendered successfully")
    return text[:MAX_BROWSER_CHARS]

def python(code: str):
    logger.info("Executing Python code")
    local_env = {}
    exec(code, {"__builtins__": {}}, local_env)
    logger.info("Python execution completed")
    return str(local_env.get("result", "ok"))

async def submit(answer, time_left_fn):
    if time_left_fn() <= 0:
        logger.error("Time limit exceeded before submission")
        return {"error": "Time limit exceeded"}

    payload = {
        "email": EMAIL,
        "secret": SECRET,
        "url": CURRENT_URL,
        "answer": answer
    }

    last_error = None

    for attempt in range(1, SUBMIT_RETRIES + 1):
        logger.info(f"Submitting answer | attempt={attempt}")

        if time_left_fn() <= 0:
            break

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(DEFAULT_SUBMIT_URL, json=payload)
                r.raise_for_status()
                logger.info("Submission response received")
                return r.json()

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Submission failed | {last_error}")
            if attempt < SUBMIT_RETRIES:
                await asyncio.sleep(SUBMIT_RETRY_DELAY)

    logger.error("Submission failed after retries")
    return {
        "error": "Submission failed after retries",
        "details": last_error
    }
