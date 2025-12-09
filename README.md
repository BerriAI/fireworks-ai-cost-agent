# Fireworks AI Cost Agent

An agent that automatically syncs Fireworks AI model pricing to the LiteLLM pricing database.

Runs as a Docker service with HTTP endpoints and automatic 24-hour scheduling.

## Features

- 🔄 **Auto-sync every 24 hours** - Automatically checks for new Fireworks models daily
- 🚀 **Instant trigger** - POST to `/trigger` to run immediately
- 📊 **Status endpoint** - Check when the next run is scheduled
- 🐳 **Docker ready** - Deploy with a single command

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FIRECRAWL_API_KEY` | ✅ | Firecrawl API key for web scraping ([get one here](https://firecrawl.dev)) |
| `GITHUB_TOKEN` | ✅ | GitHub personal access token with `repo` scope |

## Quick Start with Docker

### 1. Create a `.env` file

```bash
FIRECRAWL_API_KEY=fc-your-firecrawl-key
GITHUB_TOKEN=ghp_your-github-token
```

### 2. Run with Docker Compose

```bash
docker-compose up -d
```

### 3. Check status

```bash
curl http://localhost:8000/status
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info and available endpoints |
| `/health` | GET | Health check |
| `/status` | GET | Agent status, last run, next scheduled run |
| `/trigger` | POST | Trigger the agent to run immediately |

### Example: Trigger a run

```bash
curl -X POST http://localhost:8000/trigger
```

### Example: Check status

```bash
curl http://localhost:8000/status
```

Response:
```json
{
  "status": "idle",
  "is_running": false,
  "last_run": "2024-12-08T18:55:40.123456",
  "last_result": {
    "success": true,
    "message": "Created PR with 227 new models",
    "scraped_models": 256,
    "missing_models": 227,
    "pr_url": "https://github.com/BerriAI/litellm/pull/17692"
  },
  "next_scheduled_run": "2024-12-09T18:55:40.123456",
  "schedule_interval_hours": 24
}
```

## Running Locally (without Docker)

### 1. Install dependencies

```bash
pip install -e .
```

### 2. Set environment variables

```bash
export FIRECRAWL_API_KEY="your-firecrawl-key"
export GITHUB_TOKEN="your-github-token"
```

### 3. Run the server

```bash
python server.py
```

Or run once without the server:

```bash
python main.py
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Firecrawl     │────▶│  Model Extractor │────▶│  GitHub PR Bot  │
│   (Scraper)     │     │  (Parse & Compare│     │  (PyGithub)     │
│                 │     │   with LiteLLM)  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                                │
         │              ┌──────────────────┐              │
         └─────────────▶│   FastAPI Server │◀─────────────┘
                        │  + APScheduler   │
                        │  (24h interval)  │
                        └──────────────────┘
```

## Project Structure

```
fireworks-ai-cost-agent/
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker Compose config
├── pyproject.toml      # Python dependencies
├── README.md           # This file
├── server.py           # FastAPI server with scheduler
├── main.py             # CLI entry point
└── agent/
    ├── __init__.py
    ├── browser_agent.py  # Firecrawl scraper
    ├── compare.py        # LiteLLM comparison
    └── github_pr.py      # GitHub PR creation
```

## How it works

1. **Scraping**: Uses Firecrawl to render the Fireworks models page and extract model info (name, pricing, context window, type)

2. **Comparison**: Fetches LiteLLM's `model_prices_and_context_window.json` and identifies models not yet present

3. **PR Creation**: Creates a GitHub PR with **append-only** JSON updates (no reordering of existing entries)

4. **Scheduling**: Runs automatically every 24 hours via APScheduler

## License

MIT
