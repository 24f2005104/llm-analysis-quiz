# app/agent.py
import logging
import time
from .tools import python, submit, browse
from .llm import call_llm
from .config import TIME_LIMIT, START_TIME, MAX_AGENT_STEPS

logger = logging.getLogger(__name__)

def time_left():
    return TIME_LIMIT - (time.time() - START_TIME)


async def agent_loop(initial_url: str):
    """
    Fully autonomous quiz agent:
    - Auto-calls LLM to generate Python code per page
    - Executes safely
    - Submits answer and retries automatically if incorrect
    - Follows next URL if provided
    - Logs submission status
    """
    current_url = initial_url
    page_text = await browse(current_url)
    step = 0
    last_answer = None
    last_submit_result = None

    logger.info("Agent started")

    while current_url and step < MAX_AGENT_STEPS:
        if time_left() <= 0:
            logger.warning("Time limit exceeded, stopping agent")
            break

        step += 1
        logger.info(f"Agent step {step} | url={current_url}")

        # Call LLM to generate Python code for this page
        prompt = f"""
You are a Python agent. Given this page content, write Python code that produces the correct answer:
{page_text}

Output the result in a variable called 'result'.
"""
        try:
            llm_code = await call_llm(prompt)
            logger.info(f"LLM generated code:\n{llm_code}")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            break

        # Execute generated code safely
        try:
            result_locals = python(llm_code)
            last_answer = result_locals.get("result")
            logger.info(f"Python execution result: {last_answer}")
        except Exception as e:
            logger.error(f"Python execution failed: {e}")
            break

        # Submit answer
        response = await submit(last_answer)
        if "error" in response:
            logger.error(f"Submission failed: {response['error']}")
            break

        # Unwrap nested submission result
        submit_result = response.get("result", {}).get("submit_result", {})
        last_submit_result = submit_result
        correct = submit_result.get("correct", False)
        next_url = submit_result.get("url")

        # Log submission status
        logger.info(f"Submission status: {'Correct' if correct else 'Incorrect'} | answer={last_answer} | next_url={next_url}")

        if correct:
            if next_url:
                logger.info(f"Moving to next URL: {next_url}")
                page_text = await browse(next_url)
                current_url = next_url
            else:
                logger.info("Quiz completed successfully")
                break
        else:
            logger.warning("Answer incorrect, will retry automatically if retries remain")

    return {
        "last_answer": last_answer,
        "last_url": current_url,
        "submit_result": last_submit_result
    }
