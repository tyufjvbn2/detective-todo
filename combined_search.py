import os
from typing import List, Dict

from dotenv import load_dotenv

import requests
from slack_bolt import App

load_dotenv()

# Helper functions for each service

def search_slack(query: str, token: str) -> List[Dict]:
    """Search Slack messages using Slack Search API."""
    response = requests.get(
        "https://slack.com/api/search.messages",
        params={"query": query, "count": 5},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if response.ok and response.json().get("ok"):
        return response.json().get("messages", {}).get("matches", [])
    return []


def search_jira(query: str, base_url: str, email: str, api_token: str) -> List[Dict]:
    """Search Jira issues."""
    url = f"{base_url}/rest/api/2/search"
    jql = f"text ~ \"{query}\" order by updated desc"
    response = requests.get(
        url,
        params={"jql": jql, "maxResults": 5},
        auth=(email, api_token),
        timeout=10,
    )
    if response.ok:
        return response.json().get("issues", [])
    return []


def search_confluence(query: str, base_url: str, email: str, api_token: str) -> List[Dict]:
    """Search Confluence pages."""
    url = f"{base_url}/wiki/rest/api/search"
    response = requests.get(
        url,
        params={"cql": f"text ~ \"{query}\"", "limit": 5},
        auth=(email, api_token),
        timeout=10,
    )
    if response.ok:
        return response.json().get("results", [])
    return []


def search_drive(query: str, api_key: str) -> List[Dict]:
    """Search Google Drive files using Drive API."""
    url = "https://www.googleapis.com/drive/v3/files"
    response = requests.get(
        url,
        params={"q": f"name contains '{query}'", "pageSize": 5, "key": api_key},
        timeout=10,
    )
    if response.ok:
        return response.json().get("files", [])
    return []


# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"), signing_secret=os.environ.get("SLACK_SIGNING_SECRET"))


@app.command("/search")
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
    drive_key = os.environ.get("GOOGLE_DRIVE_API_KEY")

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

    if drive_key:
        drive_results = search_drive(query, drive_key)
        results.append({"service": "Google Drive", "items": drive_results})

    if not results:
        respond("No services configured for search.")
        return

    # Build a simple message summarizing results
    message_lines = [f"*Results for:* `{query}`\n"]
    for service in results:
        message_lines.append(f"*{service['service']}*:")
        items = service["items"]
        if not items:
            message_lines.append("- No results found.")
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
                else:  # Google Drive
                    text = item.get("name", "")
                    link = item.get("webViewLink", "")
                message_lines.append(f"- <{link}|{text}>")
        message_lines.append("")

    respond("\n".join(message_lines))


if __name__ == "__main__":
    # Run the app as a web server so Slack can send HTTP requests to the
    # command request URL. The PORT environment variable can be set by the
    # hosting platform; default to 3000 for local testing.
    app.start(port=int(os.environ.get("PORT", 3000)))
