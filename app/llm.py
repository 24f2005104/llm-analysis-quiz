# app/llm.py
import logging
import os
import httpx

logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("AIPIPE_TOKEN", "")

async def call_llm(prompt: str):
    """
    Sends prompt to LLM (Aipipe or OpenAI) and returns generated code/text
    """
    logger.info("Calling LLM API")
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    data = {"prompt": prompt, "max_tokens": 500}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.aipipe.com/v1/generate", headers=headers, json=data)
        r.raise_for_status()
        response = r.json()
        return response.get("text", "")
