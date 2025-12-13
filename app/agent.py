import asyncio
import re
from .tools import browse, python, submit
from .logger import logger
from .llm import call_llm

# Maximum steps per quiz to avoid infinite loops
MAX_AGENT_STEPS = 40

async def agent_loop(page_text, start_url, time_left_fn):
    """
    Main agent loop that:
    - Runs code provided by LLM
    - Submits answers
    - Follows next URLs automatically
    - Retries submissions until correct or time runs out
    """

    current_text = page_text
    current_url = start_url
    steps = 0
    all_results = []

    logger.info("Starting agent loop")

    while steps < MAX_AGENT_STEPS and time_left_fn() > 0:
        steps += 1
        logger.info(f"Agent step {steps} | time left: {time_left_fn():.1f}s")

        # --- Generate code from LLM ---
        try:
            # This prompt can be customized per quiz type
            prompt = f"Extract and solve quiz from the page text below. Return Python code assigning result to variable 'result'.\n\n{current_text}"
            code = await call_llm(prompt)
            if not code.strip():
                logger.warning("LLM returned empty code, skipping step")
                break
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            break

        # --- Execute Python code ---
        try:
            result = python(code)
        except Exception as e:
            logger.error(f"Python execution failed: {e}")
            result = None

        # --- Submit the result ---
        try:
            submit_resp = await submit(result, time_left_fn)
            all_results.append({
                "url": current_url,
                "answer": result,
                "submit_result": submit_resp
            })
        except Exception as e:
            logger.error(f"Submission failed: {e}")
            all_results.append({
                "url": current_url,
                "answer": result,
                "submit_result": {"error": str(e)}
            })
            break

        # --- Check if submission was correct ---
        correct = submit_resp.get("correct", False)
        if correct:
            logger.info(f"Answer correct at step {steps}")
        else:
            logger.info("Answer incorrect, retrying...")
            # Optional: wait a bit before retrying
            await asyncio.sleep(1)
            continue  # retry same step

        # --- Check for next URL ---
        next_url = None
        # Assume the page contains a link like: /demo-scrape?email=...&id=...
        match = re.search(r'(https?://[^\s"\']+)', current_text)
        if match:
            next_url = match.group(1)

        if next_url and next_url != current_url:
            current_url = next_url
            current_text = await browse(current_url)
        else:
            break  # No next URL, finish

    logger.info("Agent loop completed")
    return all_results
