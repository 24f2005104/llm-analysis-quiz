# app/tools.py
import time
import asyncio
import httpx
from playwright.async_api import async_playwright
from .config import (
    EMAIL, SECRET, DEFAULT_SUBMIT_URL,
    MAX_BROWSER_CHARS, TIME_LIMIT,
    SUBMIT_RETRIES, SUBMIT_RETRY_DELAY
)
from .logger import logger

# ------------------------------
# Safe Python executor
# ------------------------------
SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "sum": sum,
    "len": len, "range": range, "print": print, "sorted": sorted, "round": round
}

TOOLS = {}  # Will be populated dynamically

# ------------------------------
# Browser
# ------------------------------
async def browse(url: str) -> str:
    logger.info(f"Browsing URL | url={url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        text = await page.inner_text("body")
        await browser.close()
    logger.info("Page rendered successfully")
    return text[:MAX_BROWSER_CHARS]

TOOLS["browse"] = browse

# ------------------------------
# Python executor
# ------------------------------
def python(code: str):
    logger.info("Executing Python code")
    local_env = {**TOOLS}
    try:
        exec(code, {"__builtins__": SAFE_BUILTINS}, local_env)
    except Exception as e:
        logger.error(f"Python execution error: {e}")
        local_env["error"] = str(e)
    return local_env

TOOLS["python"] = python

# ------------------------------
# Submit
# ------------------------------
async def submit(answer: str, url: str):
    payload = {"email": EMAIL, "secret": SECRET, "url": url, "answer": answer}
    last_error = None
    for attempt in range(1, SUBMIT_RETRIES + 1):
        logger.info(f"Submitting answer | attempt={attempt}")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(DEFAULT_SUBMIT_URL, json=payload)
                r.raise_for_status()
                logger.info("Submission successful")
                return r.json()
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Submission failed | {last_error}")
            await asyncio.sleep(SUBMIT_RETRY_DELAY)
    logger.error("Submission failed after retries")
    return {"error": "Submission failed", "details": last_error}

TOOLS["submit"] = submit
