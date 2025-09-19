# News Agent

A Flask-based service that gathers qualitative market intelligence (news, filings, RSS feeds) and exposes it via a `/news` endpoint. A Go-powered CLI is included for conversational querying, and a Jupyter notebook mirrors the Python modules for debugging.

## Prerequisites

- Python 3.11+
- Go 1.21+
- (Optional) [NewsAPI](https://newsapi.org/) key for broader coverage. Without it, Wired RSS feeds are used by default.

## Python Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure environment variables as needed:

- `NEWSAPI_KEY` – API key for NewsAPI.
- `NEWS_AGENT_DEFAULT_LIMIT` – default number of articles to return (default `10`).
- `NEWS_AGENT_ALLOWED_DOMAINS` – comma-separated whitelist of domains.

### Run the Flask API

```bash
python app.py
```

The service listens on `http://0.0.0.0:8008` with two endpoints:

- `GET /health` – health check.
- `POST /news` – accepts JSON body `{ "query": "<term>", "limit": <int?> }` and returns an array of articles with summary and sentiment.

## CLI Chatbot

A lightweight chat-style client is available in Go under `cmd/newscli`.

```bash
go build ./cmd/newscli
./newscli -base http://localhost:8008 -limit 5
```

Or run directly:

```bash
go run ./cmd/newscli
```

The CLI prompts for search queries. Type `exit` or `quit` to leave. The default target URL is `http://localhost:8008`, but you can override with the `-base` flag or the `NEWS_AGENT_BASE_URL` environment variable.

## Jupyter Notebook

Debug or extend the agent using the provided notebook:

```bash
# Assuming the virtual environment is active
go run ./cmd/newscli
jupyter notebook notebooks/news_agent_debug.ipynb
```

The notebook mirrors all Python modules so you can tweak providers, summarization, or sentiment logic interactively.

## Testing & Validation

- `python -m compileall app.py news_agent` ensures Python modules compile.
- `go build ./cmd/newscli` confirms the CLI compiles.

## Directory Overview

- `app.py` – Flask entrypoint.
- `news_agent/` – Python package with config, providers, sentiment, summarizer, and agent orchestration.
- `cmd/newscli/` – Go CLI.
- `notebooks/news_agent_debug.ipynb` – interactive notebook.
- `requirements.txt` – Python dependencies (Flask, requests, feedparser).

## Next Steps

- Add additional providers (e.g., SEC filings) or sentiment models.
- Introduce persistence or caching for repeated queries.
- Package the CLI with release scripts or binaries.
