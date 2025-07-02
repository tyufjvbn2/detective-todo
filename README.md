# Detective Todo

This project contains a sample Slack app that performs combined search across Slack, Jira, Confluence, and Google Drive.

## Setup

1. Install Python dependencies:
   ```bash
   pip install slack_bolt requests
   ```
2. Set the following environment variables with your credentials:
   - `SLACK_BOT_TOKEN`
   - `SLACK_SIGNING_SECRET`
   - `PORT` (optional, port the server will listen on)
   - `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
   - `CONFLUENCE_BASE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`
   - `GOOGLE_DRIVE_API_KEY`

Only the Slack variables are required. The others are optional; the app will search whichever services are configured.

## Running

Launch the Slack app as a web server with:

```bash
python combined_search.py
```

Configure your slash command's Request URL to point to your server (e.g. `https://your.server/slack/events`).
Then use `/search` inside Slack to search across the configured services.
