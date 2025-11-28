# utils/submission.py
import requests
import logging

log = logging.getLogger(__name__)

def submit_answer(submit_url: str, email: str, secret: str, quiz_url: str, answer):
    payload = {
        "email": email,
        "secret": secret,
        "url": quiz_url,
        "answer": answer
    }
    log.info("Submitting to %s payload keys: %s", submit_url, list(payload.keys()))
    r = requests.post(submit_url, json=payload, timeout=30)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"status_code": r.status_code, "text": r.text}
