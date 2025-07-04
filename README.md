# Detective Todo

This project contains a sample Slack app that performs combined search across Slack, Jira, and Confluence.

## Setup

1. Install Python dependencies:
   ```bash
   pip install slack_bolt requests python-dotenv flask
   ```
2. Copy `.env.example` to `.env` and fill in your credentials. **Do not commit this file.**
3. Alternatively, set the following environment variables in your hosting environment:
   - `SLACK_BOT_TOKEN`
   - `SLACK_SIGNING_SECRET`
   - `PORT` (optional, port the server will listen on)
   - `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
   - `CONFLUENCE_BASE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`

Only the Slack variables are required. The others are optional; the app will search whichever services are configured.

## Running

Launch the Slack app as a web server with:

```bash
python combined_search.py
```

Configure your slash command's Request URL to point to your server, for example `https://your.server/search`.
Use the `/search` command inside Slack to search across the configured services.
The app also accepts the Korean variant `/검색` as an alias for `/search`.

Queries can be in Korean, English, Japanese, Chinese, or Spanish. Search
results appear as indented bullets with clickable links for easy access.
At the bottom of the response, a tiny built-in language model summarizes the
most common topics from all results.
