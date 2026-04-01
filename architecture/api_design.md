# API Architecture & Navigation Logic (Layer 2)

## Goal
To serve as the secure Navigation layer between the public-facing Vite React frontend and the backend execution tools (`tools/menu_analyzer.py`), ensuring that OpenAI API keys are never exposed to the client.

## Endpoint: `POST /analyze`

### Inputs
The endpoint expects a JSON payload matching the exact `Input Shape` defined in `gemini.md`:
*   `restaurant_name` (string)
*   `location` (string)
*   `profiles` (array of objects containing `name` and `restrictions`)

### Process Logic
1.  **Validate Input:** FastAPI and Pydantic will instantly reject malformed payloads without expending API credits.
2.  **Invoke Tool:** The request data is passed deterministically to the execution layer (`tools/menu_analyzer.py`).
3.  **Return JSON:** The Tool's raw JSON output (containing the Safe/Unsafe evaluations) is proxied directly back to the client.

### Edge Cases Handled
*   **Failed Web Scrapes / OpenAI Outages:** The endpoint will intercept execution exceptions and return a `500 Server Error` with a formatted error detail string to the frontend, preventing the React app from crashing on undefined JSON objects.
*   **CORS (Cross-Origin Resource Sharing):** Configured via Middleware to allow all origins (`*`) during local development. This must be locked down to the specific Cloudflare Pages domain prior to production deployment.
