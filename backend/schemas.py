from typing import List, Optional
from pydantic import BaseModel, Field

class ExplainRequest(BaseModel):
    url: str = Field(
        ...,
        description="The full Reddit post URL to explain (e.g. https://www.reddit.com/r/technology/comments/...)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional OpenAI model override (defaults to gpt-4o-mini)"
    )

class ExplanationResponse(BaseModel):
    explanation: List[str] = Field(
        ...,
        description="Exactly 3 to 5 bullet points explaining the post, terms, and context."
    )
    citations: List[str] = Field(
        ...,
        description="List of source URLs discovered and used by the agent during web search."
    )
