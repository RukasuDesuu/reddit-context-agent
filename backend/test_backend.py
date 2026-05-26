import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from reddit_client import RedditClient, clean_reddit_url, extract_image_url
from schemas import ExplanationResponse

class TestRedditClient(unittest.TestCase):
    def test_clean_reddit_url(self):
        url = "https://www.reddit.com/r/technology/comments/123456/title_of_post/?utm_source=share"
        cleaned = clean_reddit_url(url)
        self.assertEqual(cleaned, "https://www.reddit.com/r/technology/comments/123456/title_of_post.json")

    def test_extract_image_url_direct(self):
        post_info = {"url": "https://i.redd.it/image.png"}
        img = extract_image_url(post_info)
        self.assertEqual(img, "https://i.redd.it/image.png")

    def test_extract_image_url_hint(self):
        post_info = {"url": "https://someurl.com/abc", "post_hint": "image"}
        img = extract_image_url(post_info)
        self.assertEqual(img, "https://someurl.com/abc")

    @patch("httpx.AsyncClient.get")
    def test_fetch_and_parse_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Mock Reddit JSON payload
        mock_response.json.return_value = [
            {
                "kind": "Listing",
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {
                                "title": "Test Title",
                                "selftext": "Test body text",
                                "subreddit": "testsub",
                                "url": "https://example.com/post",
                                "post_hint": "text"
                            }
                        }
                    ]
                }
            },
            {
                "kind": "Listing",
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "author": "user1",
                                "body": "First top comment",
                                "ups": 10
                            }
                        }
                    ]
                }
            }
        ]
        mock_get.return_value = mock_response

        client = RedditClient()
        import asyncio
        result = asyncio.run(client.fetch_and_parse("https://reddit.com/r/test/comments/1"))

        self.assertEqual(result["title"], "Test Title")
        self.assertEqual(result["body"], "Test body text")
        self.assertEqual(result["subreddit"], "testsub")
        self.assertIsNone(result["image_url"])
        self.assertEqual(len(result["comments"]), 1)
        self.assertEqual(result["comments"][0]["author"], "user1")
        self.assertEqual(result["comments"][0]["body"], "First top comment")

class TestAppRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_read_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    @patch("reddit_client.RedditClient.fetch_and_parse", new_callable=AsyncMock)
    @patch("agent.RedditContextAgent.explain_post", new_callable=AsyncMock)
    def test_explain_endpoint_success(self, mock_explain, mock_fetch):
        # Setup mocks
        mock_fetch.return_value = {
            "title": "Mock Title",
            "body": "Mock Body",
            "subreddit": "mocksub",
            "image_url": None,
            "comments": []
        }
        mock_explain.return_value = ExplanationResponse(
            explanation=["Bullet 1", "Bullet 2", "Bullet 3"],
            citations=["https://source1.com"]
        )

        response = self.client.post(
            "/explain",
            json={"url": "https://reddit.com/r/mock/comments/1", "model": "gpt-4o-mini"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["explanation"]), 3)
        self.assertEqual(data["explanation"][0], "Bullet 1")
        self.assertEqual(data["citations"][0], "https://source1.com")
        mock_explain.assert_called_once()

if __name__ == "__main__":
    unittest.main()
