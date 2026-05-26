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