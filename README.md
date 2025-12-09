# Fireworks AI Cost Agent

An LLM-powered browser agent that automatically syncs Fireworks AI model pricing to the LiteLLM pricing database.

## What it does

1. **Scrapes Fireworks AI models** - Uses `browser-use` (LLM-powered browser automation) to navigate https://fireworks.ai/models and extract all model information
2. **Compares with LiteLLM** - Fetches the current `model_prices_and_context_window.json` from LiteLLM and identifies missing models
3. **Creates PRs** - Automatically files a Pull Request to add missing models to LiteLLM

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  browser-use    │────▶│  Model Extractor │────▶│  GitHub PR Bot  │
│  (Playwright +  │     │  (Parse & Compare│     │  (PyGithub)     │
│   LLM Agent)    │     │   with LiteLLM)  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Setup

### 1. Install dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Install Playwright browsers

```bash
playwright install chromium
```

### 3. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
- `OPENAI_API_KEY` - For the browser-use LLM agent (GPT-4o recommended)
- `GITHUB_TOKEN` - Personal access token with `repo` scope

## Usage

```bash
# Run the agent
python main.py

# Or with uv
uv run python main.py
```

The agent will:
1. Open a browser and navigate to Fireworks AI models page
2. Scroll through and extract all model information
3. Compare with LiteLLM's current model database
4. If missing models are found, create a PR to add them

## Project Structure

```
fireworks-ai-cost-agent/
├── pyproject.toml      # Project dependencies
├── .env.example        # Environment variable template
├── README.md           # This file
├── main.py             # Main orchestrator
└── agent/
    ├── __init__.py
    ├── browser_agent.py  # browser-use agent for scraping
    ├── compare.py        # LiteLLM comparison logic
    └── github_pr.py      # GitHub PR creation
```

## License

MIT

