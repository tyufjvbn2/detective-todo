import os
import logging
import re

from typing import List, Dict

from dotenv import load_dotenv

import requests
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request


load_dotenv()
logging.basicConfig(level=logging.DEBUG)

# Helper functions for each service

def search_slack(query: str, token: str) -> List[Dict]:
    """Search Slack messages using Slack Search API."""
    logging.debug("Searching Slack for '%s'", query)
    response = requests.get(
        "https://slack.com/api/search.messages",
        params={"query": query, "count": 5},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if response.ok and response.json().get("ok"):
        matches = response.json().get("messages", {}).get("matches", [])
        logging.debug("Slack search returned %d results", len(matches))
        return matches
    logging.debug(
        "Slack search failed with %d: %s", response.status_code, response.text
    )
    return []

def search_jira(query: str, base_url: str, email: str, api_token: str) -> List[Dict]:
    """Search Jira issues."""
    url = f"{base_url}/rest/api/2/search"
    jql = f"text ~ \"{query}\" order by updated desc"
    logging.debug("Searching Jira at %s for '%s'", base_url, query)
    response = requests.get(
        url,
        params={"jql": jql, "maxResults": 5},
        auth=(email, api_token),
        timeout=10,
    )
    if response.ok:
        issues = response.json().get("issues", [])
        logging.debug("Jira search returned %d results", len(issues))
        return issues
    logging.debug(
        "Jira search failed with %d: %s", response.status_code, response.text
    )
    return []

def search_confluence(query: str, base_url: str, email: str, api_token: str) -> List[Dict]:
    """Search Confluence pages."""
    url = f"{base_url}/wiki/rest/api/search"
    logging.debug("Searching Confluence at %s for '%s'", base_url, query)
    response = requests.get(
        url,
        params={"cql": f"text ~ \"{query}\"", "limit": 5},
        auth=(email, api_token),
        timeout=10,
    )
    if response.ok:
        results = response.json().get("results", [])
        logging.debug("Confluence search returned %d results", len(results))
        return results
    logging.debug(
        "Confluence search failed with %d: %s", response.status_code, response.text
    )
    return []


def summarize_results(results: List[Dict]) -> str:
    """Return a tiny language-model style summary of all result texts."""
    corpus = []
    for service in results:
        for item in service.get("items", []):
            if service["service"] == "Slack":
                corpus.append(item.get("text", ""))
            elif service["service"] == "Jira":
                corpus.append(item.get("fields", {}).get("summary", ""))
            elif service["service"] == "Confluence":
                corpus.append(item.get("title", ""))

    text = " ".join(corpus).lower()
    # Split on unicode word characters so queries in Korean, Japanese,
    # Chinese, and other languages are handled reasonably.
    tokens = re.findall(r"\w+", text, flags=re.UNICODE)
    stop = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "are",
        "you",
        "your",
        "have",
        "has",
        "from",
        "but",
        "not",
        "use",
        # A few very common words in Spanish
        "para",
        "los",
        "las",
    }
    freq = {}
    for tok in tokens:
        if tok in stop or len(tok) < 3:
            continue
        freq[tok] = freq.get(tok, 0) + 1

    if not freq:
        return ""

    top_words = [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]]
    return "Top topics: " + ", ".join(top_words) + "."




# Initialize Slack app and Flask server
bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


@bolt_app.command("/search")

def handle_search(ack, respond, command):
    ack()
    query = command.get("text", "")
    if not query:
        respond("Please provide a search query.")
        return

    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    jira_base = os.environ.get("JIRA_BASE_URL")
    jira_email = os.environ.get("JIRA_EMAIL")
    jira_token = os.environ.get("JIRA_API_TOKEN")
    conf_base = os.environ.get("CONFLUENCE_BASE_URL")
    conf_email = os.environ.get("CONFLUENCE_EMAIL")
    conf_token = os.environ.get("CONFLUENCE_API_TOKEN")

    results = []

    if slack_token:
        slack_results = search_slack(query, slack_token)
        results.append({"service": "Slack", "items": slack_results})

    if jira_base and jira_email and jira_token:
        jira_results = search_jira(query, jira_base, jira_email, jira_token)
        results.append({"service": "Jira", "items": jira_results})

    if conf_base and conf_email and conf_token:
        conf_results = search_confluence(query, conf_base, conf_email, conf_token)
        results.append({"service": "Confluence", "items": conf_results})

    if not results:
        respond("No services configured for search.")
        return

    # Build a simple message summarizing results
    message_lines = [f"*Results for:* `{query}`\n"]
    for service in results:
        message_lines.append(f"*{service['service']}*:")
        items = service["items"]
        if not items:
            message_lines.append("\t- No results found.")
        else:
            for item in items:
                if service["service"] == "Slack":
                    text = item.get("text", "(no text)")
                    link = item.get("permalink", "")
                elif service["service"] == "Jira":
                    key = item.get("key")
                    text = item.get("fields", {}).get("summary", "")
                    link = f"{jira_base}/browse/{key}" if key else ""
                elif service["service"] == "Confluence":
                    text = item.get("title", "")
                    link = f"{conf_base}{item.get('url', '')}" if item.get('url') else ""
                message_lines.append(f"\t\u2022 <{link}|{text}>")
        message_lines.append("")

    summary = summarize_results(results)
    if summary:
        message_lines.append("*Summary:*")
        message_lines.append(summary)

    respond("\n".join(message_lines))


@bolt_app.command("/검색")
def handle_search_korean(ack, respond, command):
    """Alias for the /search command using a Korean slash command."""
    handle_search(ack, respond, command)

@flask_app.route("/search", methods=["POST"])
def slack_events():
    """Endpoint for Slack slash command requests."""
    resp = handler.handle(request)
    if 400 <= resp.status_code < 500:
        logging.debug("/search responded with %d: %s", resp.status_code, resp.get_data(as_text=True))
    return resp


if __name__ == "__main__":
    # Run the Flask app so Slack can send slash command requests to the
    # /search endpoint. The PORT environment variable can be set by the hosting
    # platform; default to 3000 for local testing.
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
