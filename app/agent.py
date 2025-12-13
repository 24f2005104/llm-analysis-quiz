import asyncio
import re
from .tools import browse, python, submit
from .logger import logger
from .llm import call_llm

MAX_AGENT_STEPS = 40


def extract_python(code_text: str) -> str:
    """
    Extract only executable Python code from LLM output.
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
    - Generates Python via LLM
    - Executes safely
    - Submits answers
    - Follows next_url from submission response
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

RULES (STRICT):
- Output ONLY valid Python code
- No markdown, no backticks, no explanations
- Assign the final answer to variable `result`

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
        # EXECUTE PYTHON
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
            logger.warning("No result produced, retrying")
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
            break

        # ----------------------------
        # CHECK RESULT
        # ----------------------------
        if not submit_resp.get("correct", False):
            logger.info("Answer incorrect, retrying")
            current_text += (
                "\n\nPrevious answer was incorrect. "
                "Re-check calculations carefully."
            )
            await asyncio.sleep(1)
            continue

        logger.info(f"Answer correct at step {steps}")

        # ----------------------------
        # FOLLOW NEXT URL (CORRECT WAY)
        # ----------------------------
        next_url = submit_resp.get("next_url")

        if next_url:
            logger.info(f"Following next URL: {next_url}")
            current_url = next_url
            current_text = await browse(current_url)
            continue

        break  # no next quiz → done

    logger.info("Agent loop completed")
    return all_results
