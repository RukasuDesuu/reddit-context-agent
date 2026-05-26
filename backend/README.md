## Backend Architecture & Data Flow

The backend is built with FastAPI and designed around an autonomous agentic flow rather than a static pipeline. Here is the step-by-step lifecycle of a request:

### 1. Data Ingestion (Reddit Extraction)
* The client sends a raw Reddit post URL to the `/explain` endpoint.
* The backend appends `.json` to the URL, fetching the raw data directly from Reddit's public endpoints.
* A dedicated parsing utility aggressively prunes the massive JSON payload. It filters out metadata noise, isolating only the essential text: the post title, the main body (`selftext`), and the top-level comments.

### 2. Agent Initialization & Tool Calling
* The cleaned text is passed to the LLM (OpenAI).
* The LLM is initialized as an **Agent** equipped with a `search_web` tool (utilizing OpenAI's Function/Tool Calling capabilities).
* The agent analyzes the Reddit text and autonomously decides which niche terms, concepts, or implicit contexts require external knowledge. It triggers the web search tool dynamically to retrieve real-time context.

### 3. Context Synthesis & Constraint Enforcement
* Once the agent gathers sufficient context from the web, it synthesizes the information.
* A strict system prompt, coupled with Pydantic for Structured Outputs, forces the model to distill the explanation into exactly **3 to 5 bullet points**. This ensures the response is concise and adheres strictly to the assignment's formatting constraints.

### 4. Structured Response Generation
* The final output is structured into a clean JSON response containing the formatted explanation and an array of source citations (URLs) discovered during the agent's search phase.
* This response is then returned to the frontend for final rendering.

## Credits & References
- The lightweight, credential-free Reddit data extraction in `reddit_client.py` is inspired by standard public JSON API scraping patterns, similar to the approaches implemented in [reddit-json-scraper](https://github.com/0anxt/reddit-json-scraper).

---

## How to Use the API

### 1. Prerequisites
Make sure you have [uv](https://github.com/astral-sh/uv) installed.

### 2. Setup Configuration
Copy `.envsample` to a new file named `.env` and fill in your OpenAI API Key:
```env
OPENAI_API_KEY=your_actual_openai_api_key
PORT=8000
```

### 3. Run the Server
You can launch the FastAPI server locally by running:
```bash
uv run uvicorn main:app --reload
```
By default, the server will start at `http://localhost:8000`.

### 4. Endpoints

#### Health Check
- **Endpoint**: `GET /`
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "Reddit Context Agent Backend"
  }
  ```

#### Explain Reddit Post
- **Endpoint**: `POST /explain`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "url": "https://www.reddit.com/r/technology/comments/1tntmhj/post_slug/",
    "model": "gpt-4o-mini"
  }
  ```
  *(Note: `model` is optional and defaults to `gpt-4o-mini` if not specified. You can pass other OpenAI models like `gpt-4o`).*

- **Response Body**:
  ```json
  {
    "explanation": [
      "Exactly 3 to 5 bullet points explaining the post context...",
      "Further context detailing abbreviations, news, or slang...",
      "Synthesis of external information found during web search..."
    ],
    "citations": [
      "https://example.com/source-detail-1",
      "https://another-source.org/news-article"
    ]
  }
  ```

- **Example request with curl**:
  ```bash
  curl -X POST http://localhost:8000/explain \
    -H "Content-Type: application/json" \
    -d '{
      "url": "https://www.reddit.com/r/mildlyinteresting/comments/1tntmhj/i_made_a_uterus_pi%C3%B1ata_for_my_friend_who_had_a/",
      "model": "gpt-4o-mini"
    }'
  ```