#!/usr/bin/env python3
"""
Fireworks AI Cost Agent

An agent that syncs Fireworks AI model pricing to the LiteLLM model pricing database.
Uses Firecrawl to scrape models and GitHub API to create PRs.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from agent.browser_agent import scrape_fireworks_models
from agent.compare import compare_models, fetch_litellm_raw
from agent.github_pr import create_pull_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main():
    """Main orchestration function."""
    # Load environment variables
    load_dotenv()

    # Validate required environment variables
    if not os.environ.get("FIRECRAWL_API_KEY"):
        logger.error("FIRECRAWL_API_KEY environment variable is required")
        sys.exit(1)

    if not os.environ.get("GITHUB_TOKEN"):
        logger.error("GITHUB_TOKEN environment variable is required")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Fireworks AI Cost Agent")
    logger.info("=" * 60)

    # Step 1: Scrape Fireworks AI models
    logger.info("\n📡 Step 1: Scraping Fireworks AI models...")
    logger.info("Using Firecrawl to fetch https://fireworks.ai/models")

    try:
        scraped_models = await scrape_fireworks_models()
        logger.info(f"✅ Found {len(scraped_models)} models on Fireworks AI")

        if not scraped_models:
            logger.warning("No models were scraped. Exiting.")
            return

        # Log some sample models
        logger.info("\nSample models found:")
        for model in scraped_models[:5]:
            logger.info(f"  - {model.name} ({model.model_type})")

    except Exception as e:
        logger.error(f"❌ Failed to scrape Fireworks models: {e}")
        raise

    # Step 2: Fetch LiteLLM data and compare
    logger.info("\n🔍 Step 2: Comparing with LiteLLM database...")

    try:
        # Fetch raw content and parsed data
        raw_content, litellm_data = await fetch_litellm_raw()
        logger.info(f"✅ Fetched LiteLLM database ({len(litellm_data)} total models)")

        missing_models = compare_models(scraped_models, litellm_data)
        logger.info(f"📊 Found {len(missing_models)} models missing from LiteLLM")

        if not missing_models:
            logger.info("\n✨ All Fireworks models are already in LiteLLM!")
            logger.info("No PR needed.")
            return

        # Log missing models
        logger.info("\nMissing models:")
        for model in missing_models[:10]:
            logger.info(f"  - {model.name} ({model.model_id})")
        if len(missing_models) > 10:
            logger.info(f"  ... and {len(missing_models) - 10} more")

    except Exception as e:
        logger.error(f"❌ Failed to compare models: {e}")
        raise

    # Step 3: Create PR
    logger.info("\n🚀 Step 3: Creating Pull Request...")

    try:
        # Create the PR with append-only logic
        pr_url = create_pull_request(
            missing_models=missing_models,
            original_json_content=raw_content,
        )

        if pr_url:
            logger.info(f"\n✅ Successfully created Pull Request!")
            logger.info(f"🔗 PR URL: {pr_url}")
        else:
            logger.error("❌ Failed to create Pull Request")

    except Exception as e:
        logger.error(f"❌ Failed to create PR: {e}")
        raise

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"  Scraped models:    {len(scraped_models)}")
    logger.info(f"  Missing models:    {len(missing_models)}")
    logger.info(f"  PR created:        {'Yes' if pr_url else 'No'}")
    if pr_url:
        logger.info(f"  PR URL:            {pr_url}")
    logger.info("=" * 60)


def run():
    """Entry point for running the agent."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
