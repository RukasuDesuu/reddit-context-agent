import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from schemas import ExplainRequest, ExplanationResponse
from reddit_client import RedditClient, RedditClientError
from agent import RedditContextAgent

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Reddit Context Agent API",
    description="Backend API that extracts Reddit posts and runs a multimodal OpenAI agent to explain content with web context.",
    version="0.1.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "Reddit Context Agent Backend"
    }

@app.post("/explain", response_model=ExplanationResponse)
async def explain_reddit_post(payload: ExplainRequest):
    logger.info(f"Received explanation request for URL: {payload.url}")
    
    # Initialize components
    reddit = RedditClient()
    agent = RedditContextAgent()
    
    # 1. Ingest and parse Reddit post
    try:
        reddit_data = await reddit.fetch_and_parse(payload.url)
    except RedditClientError as e:
        logger.error(f"Reddit extraction failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error parsing Reddit: {e}")
        raise HTTPException(status_code=500, detail="Internal error occurred while processing the Reddit post.")

    # 2. Run OpenAI agent loop
    try:
        explanation = await agent.explain_post(reddit_data, model_override=payload.model)
        return explanation
    except Exception as e:
        logger.error(f"Agent explanation loop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
