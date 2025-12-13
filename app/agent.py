import asyncio
import re
from .tools import browse, python, submit
from .logger import logger
from .llm import call_llm

# Maximum steps per quiz to avoid infinite loops
MAX_AGENT_STEPS = 40


def extract_python(code_text: str) -> str:
    """
    Extract only executable Python code from LLM output.
    """
    if not code_text:
        return ""

    # Prefer fenced python blocks
    match = re.search(r"```python(.*?)```", code_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Any fenced block
    match = re.search(r"```(.*?)```", code_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: raw text
    return code_text.strip()


async def agent_loop(page_text, start_url, time_left_fn):
    """
    Main agent loop that:
    - Uses LLM to generate Python code
    - Executes the code safely
    - Submits answers
    - Retries intelligently
    - Follows next URLs if present
    """

    current_text = page_text
    current_url = start_url
    steps = 0
    all_results = []

    logger.info("Starting agent loop")

    while steps < MAX_AGENT_STEPS and time_left_fn() > 0:
        steps += 1
        logger.info(f"Agent step {steps} | time left: {time_left_fn():.1f}s")

        # ----------------------------
        # LLM CODE GENERATION
        # ----------------------------
        try:
            prompt = f"""
You are an automated quiz-solving agent.

TASK:
- Read the quiz from the page text.
- Compute the correct answer.

OUTPUT RULES (STRICT):
- Output ONLY valid Python code.
- Do NOT use markdown.
- Do NOT use backticks.
- Do NOT include explanations.
- The code MUST assign the final answer to a variable named `result`.
- The code MUST run without syntax errors.

PAGE TEXT:
{current_text}
"""
            llm_output = await call_llm(prompt)

            if not llm_output.strip():
                logger.warning("LLM returned empty output, retrying")
                continue

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            break

        # ----------------------------
        # EXECUTE PYTHON SAFELY
        # ----------------------------
        clean_code = extract_python(llm_output)
        logger.info("Executing Python code")

        try:
            result = python(clean_code)
        except SyntaxError as e:
            logger.error(f"Python syntax error: {e}")
            continue
        except Exception as e:
            logger.error(f"Python execution failed: {e}")
            continue

        if result is None:
            logger.warning("No result produced, retrying LLM step")
            continue

        # ----------------------------
        # SUBMIT ANSWER
        # ----------------------------
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

        # ----------------------------
        # CHECK CORRECTNESS
        # ----------------------------
        correct = submit_resp.get("correct", False)
        if correct:
            logger.info(f"Answer correct at step {steps}")
        else:
            logger.info("Answer incorrect, refining approach and retrying")
            current_text += (
                "\n\nPrevious answer was incorrect. "
                "Re-check calculations carefully and try a different approach."
            )
            await asyncio.sleep(1)
            continue

        # ----------------------------
        # FOLLOW NEXT URL (IF ANY)
        # ----------------------------
        next_url = None
        match = re.search(r'(https?://[^\s"\']+)', current_text)
        if match:
            next_url = match.group(1)

        if next_url and next_url != current_url:
            logger.info(f"Following next URL: {next_url}")
            current_url = next_url
            current_text = await browse(current_url)
        else:
            break

    logger.info("Agent loop completed")
    return all_results
