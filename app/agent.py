import asyncio
import re
from .tools import browse, python, submit
from .logger import logger
from .llm import call_llm

MAX_AGENT_STEPS = 40
MAX_FAILURES_PER_URL = 6


def extract_python(code_text: str) -> str:
    """
    Extract executable Python from LLM output.
    """
    if not code_text:
        return ""

    match = re.search(r"```python(.*?)```", code_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"```(.*?)```", code_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return code_text.strip()


async def agent_loop(page_text, start_url, time_left_fn):
    """
    Main agent loop:
    - Generate Python using LLM
    - Execute in sandbox
    - Submit answer
    - Follow next URL from submission response
    """

    current_text = page_text
    current_url = start_url
    steps = 0
    failures_for_url = 0
    last_answer = None
    all_results = []

    logger.info("Starting agent loop")

    while steps < MAX_AGENT_STEPS and time_left_fn() > 0:
        steps += 1
        logger.info(f"Agent step {steps} | time left: {time_left_fn():.1f}s")

        is_scrape_quiz = "demo-scrape" in current_url

        # ----------------------------
        # PROMPT SELECTION
        # ----------------------------
        if is_scrape_quiz:
            prompt = f"""
You are solving a WEB SCRAPING quiz.

IMPORTANT:
- The answer is ALWAYS in the PAGE TEXT
- Do NOT guess
- Do NOT reuse previous answers
- Parse text carefully

YOU MUST:
- Use string operations, loops, regex
- Extract data explicitly
- Compute deterministically

STRICT RULES:
- Output ONLY valid Python code
- No markdown, no backticks
- Allowed imports: re, math
- Assign final answer to variable `result`

PAGE TEXT:
{current_text}
"""
        else:
            prompt = f"""
You are solving a quiz.

STRICT RULES:
- Output ONLY valid Python code
- No markdown, no backticks
- Allowed imports: math, re, statistics, datetime
- Assign final answer to variable `result`

PAGE TEXT:
{current_text}
"""

        # ----------------------------
        # LLM CALL
        # ----------------------------
        try:
            llm_output = await call_llm(prompt)
            if not llm_output.strip():
                logger.warning("Empty LLM output, retrying")
                continue
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            break

        # ----------------------------
        # EXECUTE PYTHON
        # ----------------------------
        clean_code = extract_python(llm_output)
        logger.info("Executing Python code")

        try:
            result = python(clean_code)
        except Exception as e:
            logger.error(f"Python execution failed: {e}")
            continue

        if result is None:
            logger.warning("No result produced")
            continue

        # ----------------------------
        # SAME ANSWER GUARD
        # ----------------------------
        if result == last_answer:
            failures_for_url += 1
            logger.error("Same answer repeated multiple times — forcing rethink")
            current_text += (
                "\n\nPrevious answer was incorrect.\n"
                "Re-parse the PAGE TEXT carefully.\n"
                "Check indexes, conditions, and counts."
            )
            await asyncio.sleep(1)
            if failures_for_url >= MAX_FAILURES_PER_URL:
                logger.error(f"Too many failures on {current_url}, stopping")
                break
            continue

        last_answer = result

        # ----------------------------
        # SUBMIT ANSWER
        # ----------------------------
        submit_resp = await submit(result, time_left_fn)
        all_results.append({
            "url": current_url,
            "answer": result,
            "submit_result": submit_resp
        })

        if not submit_resp.get("correct", False):
            failures_for_url += 1
            logger.info("Answer incorrect")
            if failures_for_url >= MAX_FAILURES_PER_URL:
                logger.error(f"Too many failures on {current_url}, stopping")
                break
            current_text += (
                "\n\nThe answer was WRONG.\n"
                "Try a DIFFERENT extraction approach.\n"
                "Do NOT reuse logic."
            )
            await asyncio.sleep(1)
            continue

        # ----------------------------
        # ANSWER CORRECT
        # ----------------------------
        logger.info(f"Answer correct at step {steps}")
        failures_for_url = 0
        last_answer = None

        # ----------------------------
        # FOLLOW NEXT URL (FROM RESPONSE)
        # ----------------------------
        next_url = submit_resp.get("url")

        if next_url and next_url != current_url:
            logger.info(f"Following next URL: {next_url}")
            current_url = next_url
            current_text = await browse(current_url)
            continue

        break  # No next quiz

    logger.info("Agent loop completed")
    return all_results
