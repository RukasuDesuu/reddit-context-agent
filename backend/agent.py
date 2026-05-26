import os
import logging
from typing import Dict, List, Set, Optional
from openai import OpenAI
from ddgs import DDGS
from schemas import ExplanationResponse

logger = logging.getLogger(__name__)

def search_web(query: str, client: OpenAI, max_results: int = 15, top_k: int = 5) -> str:
    """
    Performs a DuckDuckGo web search, chunks the results, embeds them using OpenAI,
    ranks them by semantic similarity to the query, and returns the top_k most relevant chunks.
    """
    logger.info(f"Executing semantic web search for: {query}")
    try:
        # 1. Fetch more raw results from DuckDuckGo
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No search results found."

        # 2. Extract text and metadata for each result
        chunks = []
        for r in results:
            title = r.get("title", "No Title")
            href = r.get("href", "")
            body = r.get("body", "")
            if not body:
                continue
            
            # Text to embed
            text_to_embed = f"Title: {title}. Snippet: {body}"
            chunks.append({
                "title": title,
                "url": href,
                "body": body,
                "text_to_embed": text_to_embed
            })

        if not chunks:
            return "No valid search result content found."

        # 3. Generate embeddings in batch for all chunks
        logger.info(f"Generating embeddings for {len(chunks)} search chunks")
        chunk_texts = [c["text_to_embed"] for c in chunks]
        
        # We call OpenAI embeddings API
        embedding_response = client.embeddings.create(
            input=chunk_texts,
            model="text-embedding-3-small"
        )
        doc_vectors = [data.embedding for data in embedding_response.data]

        # Generate embedding for the query
        query_response = client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_vector = query_response.data[0].embedding

        # 4. Compute cosine similarities using numpy
        import numpy as np
        q = np.array(query_vector)
        docs = np.array(doc_vectors)
        
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm
            
        doc_norms = np.linalg.norm(docs, axis=1, keepdims=True)
        doc_norms[doc_norms == 0] = 1.0
        docs = docs / doc_norms
        
        similarities = np.dot(docs, q)

        # Associate similarity score with each chunk
        for idx, score in enumerate(similarities):
            chunks[idx]["score"] = float(score)

        # 5. Sort chunks by similarity score descending
        chunks.sort(key=lambda x: x["score"], reverse=True)

        # 6. Format and return the top_k chunks
        top_chunks = chunks[:top_k]
        formatted = []
        for c in top_chunks:
            formatted.append(
                f"Title: {c['title']}\n"
                f"URL: {c['url']}\n"
                f"Snippet: {c['body']}\n"
                f"Relevance Score: {c['score']:.4f}\n"
                f"---"
            )
        return "\n".join(formatted)

    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return f"Error performing search: {str(e)}"

# Schema for the search tool to be passed to OpenAI
SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search the web to retrieve real-time context, explain slang, abbreviations, "
            "niche concepts, memes, or news events mentioned in the Reddit post."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the web."
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    }
}

class RedditContextAgent:
    def __init__(self, api_key: Optional[str] = None):
        # Fallback to env variable if not provided
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            logger.warning("OpenAI API key not set or is using placeholder value.")
        self.client = OpenAI(api_key=self.api_key)

    async def explain_post(self, reddit_data: Dict, model_override: Optional[str] = None) -> ExplanationResponse:
        """
        Runs the agent loop. Feeds the Reddit data (including images) to OpenAI,
        handles tool calls to search the web, and returns the final structured explanation.
        """
        # Resolve model: use model_override if provided, else default to gpt-4o-mini
        model = model_override or "gpt-4o-mini"
        logger.info(f"Starting agent loop using model: {model}")

        system_prompt = (
            "You are an expert context retriever and explainer agent.\n"
            "Your goal is to explain the context, terms, references, and meaning of the provided Reddit post.\n"
            "You are equipped with a `search_web` tool to search the internet for terms, abbreviations, events, memes, or slang that you are not fully certain about.\n"
            "DO NOT guess or assume context if you lack information. Use the `search_web` tool aggressively to verify facts and gather background context.\n\n"
            "Follow these strict constraints:\n"
            "1. Explain the post in exactly 3 to 5 clear, concise, and informative bullet points.\n"
            "2. Provide a list of all URLs you visited and used to synthesize the explanation in the 'citations' field of your response.\n"
            "3. Keep the explanation objective, clear, and focused on clarifying terms and contextual background."
        )

        # Build user message content (multimodal if image is present)
        comments_str = ""
        for i, c in enumerate(reddit_data.get("comments", [])):
            comments_str += f"Comment {i+1} by u/{c.get('author')}: {c.get('body')} (Upvotes: {c.get('ups')})\n\n"

        text_content = (
            f"Subreddit: r/{reddit_data.get('subreddit')}\n"
            f"Title: {reddit_data.get('title')}\n"
            f"Body:\n{reddit_data.get('body')}\n\n"
            f"Top Comments:\n{comments_str}"
        )

        user_content = [{"type": "text", "text": text_content}]

        image_url = reddit_data.get("image_url")
        if image_url:
            logger.info(f"Including image in agent input: {image_url}")
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            })

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        # Track search URLs returned by the tool (as backup/verification)
        search_urls: Set[str] = set()

        # Run completion loop (up to 5 iterations of tool calling)
        for iteration in range(5):
            logger.info(f"Agent iteration {iteration + 1}")
            try:
                # We use beta.chat.completions.parse for structured output support
                response = self.client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    tools=[SEARCH_TOOL],
                    response_format=ExplanationResponse,
                )
            except Exception as e:
                logger.error(f"OpenAI completion error: {e}")
                raise RuntimeError(f"OpenAI completion request failed: {str(e)}")

            message = response.choices[0].message
            tool_calls = message.tool_calls

            if not tool_calls:
                # No more tools requested. The response should contain parsed content.
                parsed_response = message.parsed
                if parsed_response:
                    # Enforce citations collected from tools if model list is empty or to enrich it
                    model_citations = set(parsed_response.citations)
                    # We can union them or make sure they match. Let's make sure all model citations are validated,
                    # and if the model citations are empty, fill them with our search_urls.
                    if not model_citations and search_urls:
                        parsed_response.citations = list(search_urls)
                    return parsed_response
                else:
                    raise RuntimeError("Failed to receive structured parse response from OpenAI.")

            # Append the assistant's message with tool calls to the history
            messages.append(message)

            # Process tool calls
            for tool_call in tool_calls:
                if tool_call.function.name == "search_web":
                    import json
                    try:
                        args = json.loads(tool_call.function.arguments)
                        query = args.get("query", "")
                    except Exception as e:
                        logger.error(f"Failed to parse tool arguments: {e}")
                        query = ""

                    # Run search
                    search_result = search_web(query, client=self.client)
                    
                    # Track URLs returned in search results
                    # Simple extraction: search for 'URL: ' lines
                    for line in search_result.split("\n"):
                        if line.startswith("URL: "):
                            url = line[5:].strip()
                            if url:
                                search_urls.add(url)

                    # Append tool response
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": search_result
                    })

        raise RuntimeError("Agent exceeded maximum search iterations without returning a structured response.")
