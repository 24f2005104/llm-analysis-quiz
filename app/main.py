from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from .agent import agent_loop
from .tools import browse
from .config import SECRET, TIME_LIMIT
from .logger import logger
import time

# ------------------------------
# FastAPI app setup
# ------------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ------------------------------
# Request model
# ------------------------------
class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

# ------------------------------
# Quiz endpoint
# ------------------------------
@app.post("/quiz")
async def quiz(payload: QuizRequest):
    logger.info(f"Quiz request received | url={payload.url} | email={payload.email}")

    # Secret verification
    if payload.secret != SECRET:
        logger.warning(f"Invalid secret from {payload.email}")
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Start timer for this request
    start_time = time.time()
    def time_left():
        return TIME_LIMIT - (time.time() - start_time)

    try:
        # Fetch initial page content
        page_text = await browse(payload.url)
        logger.info("Initial page fetched, starting agent loop")

        # Run agent loop (auto-follows next URLs)
        final_result = await agent_loop(page_text, payload.url, time_left)

        logger.info("Agent loop completed")
        return {
            "status": "success",
            "result": final_result
        }

    except Exception as e:
        logger.error(f"Quiz processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
