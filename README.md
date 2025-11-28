# llm-analysis-quiz

Solver endpoint for the LLM Analysis Quiz (TDS 2025). This project listens for POST requests with
{"email","secret","url"} and attempts to solve the quiz at `url` and submit the answer.

## Setup (Windows PowerShell)

1. Clone repo:
   git clone https://github.com/<your-username>/llm-analysis-quiz.git
   cd llm-analysis-quiz

2. Create a virtual env (optional but recommended):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

3. Install dependencies:
   pip install -r requirements.txt

4. Install Playwright browsers:
   playwright install chromium

5. Copy `.env.example` → `.env` and fill in your values:
   - QUIZ_SECRET must exactly match what you put in the Google Form.
   - QUIZ_EMAIL your student email
   - AIPIPE_API_KEY your OpenAI/AIPipe key if needed

   Example (PowerShell):
   cp .env.example .env
   # then edit .env in an editor and save

6. Run the server:
   uvicorn main:app --reload --port 8000

7. Test with the demo:
   curl -X POST http://localhost:8000/solve -H "Content-Type: application/json" -d "{\"email\":\"you@example.com\",\"secret\":\"sH@un@k-Lab-2025\",\"url\":\"https://tds-llm-analysis.s-anand.net/demo\"}"

## Deploy
Deploy to any container platform (Render, Fly, Railway, Cloud Run). Make sure to set env vars:
QUIZ_SECRET, QUIZ_EMAIL, AIPIPE_API_KEY.

## Files
- main.py: FastAPI endpoint + security checks
- quiz_solver.py: main solving logic (uses Playwright)
