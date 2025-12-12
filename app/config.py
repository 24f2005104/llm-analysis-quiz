import os
import time

EMAIL = os.environ.get("EMAIL")
SECRET = os.environ.get("SECRET")
AIPIPE_TOKEN = os.environ.get("AIPIPE_TOKEN")

AIPIPE_URL = "https://aipipe.org/openai/v1/chat/completions"
MODEL = "gpt-4.1-mini"

DEFAULT_SUBMIT_URL = "https://tds-llm-analysis.s-anand.net/submit"

MAX_BROWSER_CHARS = 15000
MAX_AGENT_STEPS = 40

SUBMIT_RETRIES = 3
SUBMIT_RETRY_DELAY = 2  # seconds

TIME_LIMIT = 170  # seconds
START_TIME = time.time()
