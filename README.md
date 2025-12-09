# Fireworks AI Cost Agent

An agent that automatically syncs Fireworks AI model pricing to the LiteLLM pricing database.

## What it does

1. **Scrapes Fireworks AI models** - Uses Firecrawl API to fetch all models from https://fireworks.ai/models
2. **Compares with LiteLLM** - Fetches the current `model_prices_and_context_window.json` from LiteLLM and identifies missing models
3. **Creates PRs** - Automatically files a Pull Request to add missing models to LiteLLM

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Firecrawl     │────▶│  Model Extractor │────▶│  GitHub PR Bot  │
│   (Scraper)     │     │  (Parse & Compare│     │  (PyGithub)     │
│                 │     │   with LiteLLM)  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Setup

### 1. Install dependencies

```bash
pip install -e .
```

### 2. Set up environment variables

```bash
export FIRECRAWL_API_KEY="your-firecrawl-api-key"
export GITHUB_TOKEN="your-github-token"
```

Required environment variables:
- `FIRECRAWL_API_KEY` - Firecrawl API key for web scraping
- `GITHUB_TOKEN` - GitHub personal access token with `repo` scope (or fine-grained with Contents + Pull requests write access)

## Usage

```bash
python main.py
```

The agent will:
1. Scrape all models from Fireworks AI using Firecrawl
2. Compare with LiteLLM's current model database
3. If missing models are found, create a PR to add them

## Project Structure

```
fireworks-ai-cost-agent/
├── pyproject.toml      # Project dependencies
├── README.md           # This file
├── main.py             # Main orchestrator
└── agent/
    ├── __init__.py
    ├── browser_agent.py  # Firecrawl scraper for Fireworks models
    ├── compare.py        # LiteLLM comparison logic
    └── github_pr.py      # GitHub PR creation (append-only)
```

## How it works

### Scraping
Uses Firecrawl to render the JavaScript-heavy Fireworks models page and extract model information including:
- Model name and ID
- Pricing (input/output or unified)
- Context window
- Model type (LLM, Vision, Image, Audio, Embedding, Reranker)

### Comparison
Fetches the LiteLLM `model_prices_and_context_window.json` and compares normalized model IDs to find models not yet in LiteLLM.

### PR Creation
Uses **append-only** JSON modification to preserve the original file structure and only add new entries at the end. This ensures clean PRs with only additions, no spurious deletions from JSON reordering.

## License

MIT
