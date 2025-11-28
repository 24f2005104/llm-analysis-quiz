# solver/llm.py
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

# ---------------------------
# Synchronous LLM function
# ---------------------------
def solve_with_llm(quiz_data: dict) -> dict:
    """
    Synchronous function to call your LLM or fallback logic.
    Replace this with your actual LLM API call.
    """
    logging.info("Solving quiz with LLM (sync)...")
    
    # Example fallback: just returns empty answers
    # Replace this with real API call logic if needed
    return {"answer": {}, "solved": True}

# ---------------------------
# Async wrapper for quiz_solver
# ---------------------------
async def solve_with_llm_async(quiz_data: dict) -> dict:
    """
    Async wrapper around the synchronous LLM function.
    Allows usage in async FastAPI endpoints without blocking.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, solve_with_llm, quiz_data)
    return result
