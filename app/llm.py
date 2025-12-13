# app/llm.py
import logging
import os
import httpx

logger = logging.getLogger(__name__)

AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")

AIPIPE_URL = "https://aipipe.org/openai/v1/chat/completions"

async def call_llm(prompt: str) -> str:
    """
    Calls AI Pipe (OpenAI-compatible Chat Completions API)
    """
    if not AIPIPE_TOKEN:
        raise RuntimeError("AIPIPE_TOKEN not set")

    logger.info("Calling LLM via AI Pipe")

    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful reasoning assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(AIPIPE_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]
