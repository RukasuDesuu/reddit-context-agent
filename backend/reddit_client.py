import html
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse
import httpx

logger = logging.getLogger(__name__)

def clean_reddit_url(url: str) -> str:
    """
    Cleans and formats a Reddit post URL to append '.json' properly.
    Strips query parameters and appends '.json' if not present.
    """
    parsed = urlparse(url)
    # Rebuild path to remove trailing slash and append .json
    path = parsed.path.rstrip("/")
    if not path.endswith(".json"):
        path += ".json"
    
    # We rebuild the URL without query parameters or fragments
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))

def extract_image_url(post_info: dict) -> Optional[str]:
    """
    Attempts to extract a direct image URL from the Reddit post info.
    Handles standard images, preview images, and media metadata (galleries).
    """
    # 1. Check if the main URL points to an image extension
    url = post_info.get("url", "")
    if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
        return url

    # 2. Check if the post hint is "image"
    if post_info.get("post_hint") == "image":
        return url

    # 3. Check media_metadata (usually galleries or embedded images)
    media_metadata = post_info.get("media_metadata")
    if isinstance(media_metadata, dict):
        for item_id, item_data in media_metadata.items():
            if item_data.get("status") == "valid" and item_data.get("e") == "Image":
                s_data = item_data.get("s", {})
                img_url = s_data.get("u")
                if img_url:
                    return html.unescape(img_url)

    # 4. Check preview images
    preview = post_info.get("preview", {})
    images = preview.get("images", [])
    if images and isinstance(images, list):
        source = images[0].get("source", {})
        img_url = source.get("url")
        if img_url:
            return html.unescape(img_url)

    return None

class RedditClientError(Exception):
    """Base exception for Reddit Client errors."""
    pass

class RedditClient:
    def __init__(self, user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"):
        self.headers = {"User-Agent": user_agent}

    async def fetch_and_parse(self, post_url: str) -> Dict:
        """
        Fetches the raw JSON for a Reddit post, prunes metadata, and returns clean structure.
        """
        cleaned_url = clean_reddit_url(post_url)
        logger.info(f"Fetching Reddit data from: {cleaned_url}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(cleaned_url, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching Reddit data: {e}")
                raise RedditClientError(f"Reddit API returned HTTP status {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"Network error fetching Reddit data: {e}")
                raise RedditClientError("Failed to reach Reddit servers")
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"Error parsing Reddit JSON response: {e}")
                raise RedditClientError("Failed to parse Reddit response JSON")

        if not isinstance(data, list) or len(data) < 1:
            raise RedditClientError("Unexpected Reddit JSON response format (expected a list of listings)")

        # Extract post data (first element in the array)
        try:
            post_listing = data[0]
            post_children = post_listing.get("data", {}).get("children", [])
            if not post_children:
                raise RedditClientError("No post data found in the Reddit response")
            
            post_info = post_children[0].get("data", {})
        except (IndexError, KeyError, AttributeError) as e:
            logger.error(f"Error extracting post info: {e}")
            raise RedditClientError("Failed to extract post content")

        title = post_info.get("title", "")
        selftext = post_info.get("selftext", "")
        subreddit = post_info.get("subreddit", "")
        image_url = extract_image_url(post_info)

        # Extract comments (second element in the array, if exists)
        comments: List[Dict] = []
        if len(data) > 1:
            try:
                comments_listing = data[1]
                comments_children = comments_listing.get("data", {}).get("children", [])
                
                count = 0
                for child in comments_children:
                    if count >= 10:
                        break
                    
                    if child.get("kind") == "t1":  # t1 represents comment objects
                        comment_data = child.get("data", {})
                        body = comment_data.get("body", "")
                        author = comment_data.get("author", "")
                        ups = comment_data.get("ups", 0)
                        
                        # Ignore deleted comments or empty comments
                        if body and body != "[deleted]" and body != "[removed]":
                            comments.append({
                                "author": author,
                                "body": body.strip(),
                                "ups": ups
                            })
                            count += 1
            except Exception as e:
                logger.warning(f"Error extracting comments: {e}. Proceeding without comments.")

        return {
            "title": title,
            "body": selftext,
            "subreddit": subreddit,
            "image_url": image_url,
            "comments": comments
        }
