## Backend Architecture & Data Flow

The backend is built with FastAPI and designed around an autonomous agentic flow rather than a static pipeline. Here is the step-by-step lifecycle of a request:

### 1. Data Ingestion (Reddit Extraction)
* The client sends a raw Reddit post URL to the `/explain` endpoint.
* The backend appends `.json` to the URL, fetching the raw data directly from Reddit's public endpoints.
* A dedicated parsing utility aggressively prunes the massive JSON payload. It filters out metadata noise, isolating only the essential text: the post title, the main body (`selftext`), and the top-level comments.

### 2. Agent Initialization & Tool Calling (with Transient RAG)
* The cleaned text is passed to the LLM (OpenAI).
* The LLM is initialized as an **Agent** equipped with a `search_web` tool.
* **Transient RAG Pipeline**: To optimize the LLM context window and filter out web noise:
  1. The `search_web` tool queries the web to retrieve a larger set of search results (10-15 results).
  2. The results are split into smaller text chunks.
  3. It generates embeddings for the query and all chunks using OpenAI's `text-embedding-3-small` model.
  4. It calculates semantic similarity in-memory using `numpy` (without requiring a persistent database), selecting only the top-K most relevant chunks.
  5. The agent receives only this highly curated, relevant context to construct its explanation.

### 3. Context Synthesis & Constraint Enforcement
* Once the agent gathers sufficient context from the web, it synthesizes the information.
* A strict system prompt, coupled with Pydantic for Structured Outputs, forces the model to distill the explanation into exactly **3 to 5 bullet points**. This ensures the response is concise and adheres strictly to the assignment's formatting constraints.

### 4. Structured Response Generation
* The final output is structured into a clean JSON response containing the formatted explanation and an array of source citations (URLs) discovered during the agent's search phase.
* This response is then returned to the frontend for final rendering.

## Architectural Decisions: In-Memory Transient RAG

Rather than integrating a heavy local vector database (like `faiss-cpu`) or loading heavy transformer model weights locally for semantic search, the system uses an **In-Memory Transient RAG** approach:
- **Lightweight Dependencies**: Calculating cosine similarity using `numpy` avoids importing and compiling heavy C++ library bindings like `faiss-cpu`, ensuring seamless installation across platforms 
- **Fast Execution & Low Footprint**: The retrieval is transient and scoped to the lifecycle of a single HTTP request. For 10-15 search results broken into ~40 chunks, a simple cosine similarity calculation in memory executes in a few milliseconds, without the overhead of disk operations or maintaining database server connections.
- **Cost-Effective Semantic Quality**: Using OpenAI's `text-embedding-3-small` provides state-of-the-art vector representations for cents ($0.02 per million tokens), matching the quality of local models without downloading gigabytes of model weights.

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

---

## Example Output & Quality Comparison

Here is an example demonstrating the impact of the **In-Memory Transient RAG** when querying a Minecraft post from `r/feedthebeast` (`https://www.reddit.com/r/feedthebeast/comments/1tnjexc/farmhouse_again/`):

### Standard Non-RAG Search (Baseline)
Without semantic filtering, the web search returns generic pages about "Feed The Beast". The explanation focuses on general concepts rather than the post itself:
```json
{
  "explanation": [
    "The post features a visually impressive Minecraft farmhouse creation, reflecting the game's aesthetics and community's creativity in building structures...",
    "Feed The Beast, or FTB, is a modding community for Minecraft that focuses on enhancing gameplay through various modifications...",
    "The enthusiastic comment from u/Hixmet emphasizes admiration for the build, typical of the supportive and creative culture in Minecraft..."
  ],
  "citations": [
    "https://www.quora.com/Why-do-people-call-modded-Minecraft-feed-the-beast...",
    "https://feed-the-beast.com/",
    "https://feed-the-beast.fandom.com/wiki/Feed_The_Beast"
  ]
}
```

### In-Memory Transient RAG Search (Active)
With RAG, the query is embedded, and the system fetches more results, ranking them semantically. The returned chunks are highly contextualized to the specific post (such as recognizing structural features like domes/windmills and referencing a similar previous post):
```json
{
  "explanation": [
    "The post showcases a beautifully designed farmhouse in Minecraft, featuring a whimsical style with unique architectural elements like domes and a windmill.",
    "It highlights the creativity within the Minecraft community, particularly in the r/feedthebeast subreddit, which focuses on modded gameplay...",
    "The comment from user u/Hixmet shows appreciation for the design and expresses a desire to replicate similar builds..."
  ],
  "citations": [
    "https://www.reddit.com/r/feedthebeast/comments/1t4h7ar/farmhouse/",
    "https://ftbwiki.org/",
    "https://www.minecraft-schematics.com/schematic/19818/"
  ]
}
```