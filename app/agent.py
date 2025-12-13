import asyncio
import re
from .tools import browse, python, submit
from .logger import logger
from .llm import call_llm

MAX_AGENT_STEPS = 40
MAX_RETRIES_PER_URL = 6
MAX_SAME_ANSWER_REPEAT = 3


def extract_python(code_text: str) -> str:
    """
    Extract executable Python code from LLM output.
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
    Automated quiz-solving agent:
    - Reads page text
    - Uses LLM to generate Python
    - Executes in sandbox
    - Submits answers
    - Follows next quiz URLs
    - Avoids infinite loops
    """

    current_text = page_text
    current_url = start_url

    steps = 0
    all_results = []

    # Safety trackers
    url_failures = {}
    last_answer = None
    same_answer_count = 0

    logger.info("Starting agent loop")

    while steps < MAX_AGENT_STEPS and time_left_fn() > 0:
        steps += 1
        logger.info(f"Agent step {steps} | time left: {time_left_fn():.1f}s")

        # ----------------------------
        # LLM PROMPT
        # ----------------------------
        prompt = f"""
You are an automated quiz-solving agent.

TASK:
- Read the quiz from PAGE TEXT
- Compute the correct answer

STRICT RULES:
- Output ONLY valid Python code
- No markdown, no backticks
- Do NOT import third-party libraries
- Allowed imports: math, re, statistics, datetime
- Do NOT use requests, httpx, pandas, numpy, playwright
- The final answer MUST be assigned to variable `result`

IMPORTANT:
- If data must be extracted, PARSE it explicitly from PAGE TEXT
- Do NOT guess
- Use string / regex logic if needed

PAGE TEXT:
{current_text}
"""

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
            logger.warning("No result produced, retrying")
            continue

        # ----------------------------
        # STAGNATION CHECK
        # ----------------------------
        if result == last_answer:
            same_answer_count += 1
        else:
            same_answer_count = 0

        last_answer = result

        if same_answer_count >= MAX_SAME_ANSWER_REPEAT:
            logger.error("Same answer repeated multiple times — forcing rethink")
            current_text += (
                "\n\nIMPORTANT: You are repeating the same wrong answer. "
                "You MUST change strategy, parsing logic, or interpretation."
            )
            same_answer_count = 0
            continue

        # ----------------------------
        # SUBMIT ANSWER
        # ----------------------------
        submit_resp = await submit(result, time_left_fn)

        all_results.append({
            "url": current_url,
            "answer": result,
            "submit_result": submit_resp
        })

        # ----------------------------
        # HANDLE INCORRECT ANSWER
        # ----------------------------
        if not submit_resp.get("correct", False):
            logger.info("Answer incorrect")

            url_failures[current_url] = url_failures.get(current_url, 0) + 1
            if url_failures[current_url] >= MAX_RETRIES_PER_URL:
                logger.error(f"Too many failures on {current_url}, stopping")
                break

            reason = submit_resp.get("reason")
            feedback = "Previous answer was incorrect."
            if reason:
                feedback += f" Server feedback: {reason}"

            current_text += f"\n\n{feedback}\nTry a different reasoning approach."
            await asyncio.sleep(1)
            continue

        logger.info(f"Answer correct at step {steps}")

        # ----------------------------
        # FOLLOW NEXT QUIZ URL
        # ----------------------------
        next_url = submit_resp.get("url")

        if next_url and next_url != current_url:
            logger.info(f"Following next URL: {next_url}")
            current_url = next_url
            current_text = await browse(current_url)
            last_answer = None
            same_answer_count = 0
            continue

        # No next quiz
        break

    logger.info("Agent loop completed")
    return all_results
