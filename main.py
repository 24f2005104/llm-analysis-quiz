# ...existing code...
import logging
import asyncio
import time
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from solver.quiz_solver import solve_quiz_async

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# ...existing code...
import os
from dotenv import load_dotenv

# load .env file into environment
load_dotenv()

# Define your secret (get from Google Form)
VALID_SECRET = os.getenv("QUIZ_SECRET")
QUIZ_EMAIL = os.getenv("QUIZ_EMAIL")
AIPIPE_KEY = os.getenv("AIPIPE_KEY")

if not VALID_SECRET:
    raise ValueError("QUIZ_SECRET environment variable not set")
# ...existing code...

class SolveRequest(BaseModel):
    email: str
    secret: str
    url: str


@app.post("/solve")
async def solve_endpoint(payload: SolveRequest):
    # Validate secret
    if payload.secret != VALID_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    logging.info(f"Received quiz URL: {payload.url}")
    
    start_ts = time.time()
    timeout_seconds = 180  # 3 minutes total for this quiz session
    current_url = payload.url
    last_submission = None

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        while (time.time() - start_ts) < timeout_seconds:
            # Solve the current URL
            result = await solve_quiz_async(current_url)
            if not result.get("solved"):
                logging.warning(f"Quiz fallback used for {payload.email} at {current_url}")
                break

            submit_url = result.get("submit_url")
            answer = result.get("answer")
            if not submit_url:
                logging.warning("No submit URL found on page; stopping.")
                break

            # Build submission payload
            submit_payload = {
                "email": payload.email,
                "secret": payload.secret,
                "url": current_url,
                "answer": answer
            }

            logging.info(f"Submitting answer to {submit_url}")
            try:
                resp = await client.post(submit_url, json=submit_payload)
                last_submission = {"status_code": resp.status_code, "text": resp.text}
                if resp.status_code != 200:
                    logging.warning(f"Submit returned non-200: {resp.status_code}")
                    break

                resp_json = resp.json()
                logging.info(f"Submit response: {resp_json}")

                # --- NEW LOGIC START ---
                # Even if incorrect, the question is still open for 300s.
                # If the server returns next URL, we may continue;
                # If not, we retry SAME question until 300s expires.
                if resp_json.get("correct"):
                    if resp_json.get("url"):
                        current_url = resp_json["url"]
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        break  # correct, no next question
                else:
                    # Incorrect answer — retry SAME question if time remains
                    logging.info("Incorrect answer — retrying same question until timeout.")
                    await asyncio.sleep(0.5)
                    continue
                # --- NEW LOGIC END ---

            except Exception as e:
                logging.error(f"Error while submitting answer: {e}")
                break

    return {
        "email": payload.email,
        "start_url": payload.url,
        "last_submission": last_submission,
        "elapsed_seconds": time.time() - start_ts
    }


# ...existing code...
