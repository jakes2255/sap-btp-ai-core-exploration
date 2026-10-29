
import os
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

NEWS_API_URL = "https://hn.algolia.com/api/v1/search_by_date"

DEFAULT_QUERY = "artificial intelligence OR LLM OR AI agents"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/news")
def get_news():
    query = request.args.get("q", DEFAULT_QUERY).strip()
    limit = request.args.get("limit", default=20, type=int)

    if not query:
        return jsonify({"error": "Please provide a search query."}), 400

    # Keep requests within a reasonable range.
    limit = max(1, min(limit, 50))

    try:
        response = requests.get(
            NEWS_API_URL,
            params={
                "query": query,
                "tags": "story",
                "hitsPerPage": limit,
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()

        articles = []

        for story in payload.get("hits", []):
            title = story.get("title") or story.get("story_title")
            url = story.get("url") or story.get("story_url")

            if not title or not url:
                continue

            created_at = story.get("created_at")
            published = None

            if created_at:
                try:
                    published = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    ).isoformat()
                except ValueError:
                    published = created_at

            articles.append({
                "id": story.get("objectID"),
                "title": title,
                "url": url,
                "author": story.get("author", "Unknown"),
                "published_at": published,
                "points": story.get("points") or 0,
                "comments": story.get("num_comments") or 0,
            })

        return jsonify({
            "query": query,
            "count": len(articles),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "Hacker News via Algolia",
            "articles": articles,
        })

    except requests.RequestException:
        app.logger.exception("Unable to retrieve news")
        return jsonify({
            "error": "The news service is temporarily unavailable. "
                     "Please try again."
        }), 502

    except ValueError:
        app.logger.exception("Invalid JSON from news service")
        return jsonify({
            "error": "The news service returned an invalid response."
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
