# LLM Quiz Agent

An autonomous LLM-powered agent that solves JavaScript-rendered data quizzes.

## Features
- Headless browser scraping (Playwright)
- LLM-driven reasoning and Python execution
- Automatic retries within time limits
- Fixed evaluation submission endpoint
- Audio / image extensible

## Endpoint

POST /quiz

```json
{
  "email": "you@example.com",
  "secret": "your-secret",
  "url": "https://tds-llm-analysis.s-anand.net/demo"
}
