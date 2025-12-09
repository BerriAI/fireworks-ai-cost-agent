"""
Fireworks AI Cost Agent - Web Server

Provides HTTP endpoints to trigger and monitor the model sync agent.
Automatically runs every 24 hours.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

from agent.browser_agent import scrape_fireworks_models
from agent.compare import compare_models, fetch_litellm_raw
from agent.github_pr import create_pull_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Fireworks AI Cost Agent",
    description="Syncs Fireworks AI model pricing to LiteLLM",
    version="1.0.0",
)

# Scheduler
scheduler = AsyncIOScheduler()

# Global state
class AgentState:
    last_run: Optional[datetime] = None
    last_result: Optional[dict] = None
    is_running: bool = False
    next_scheduled_run: Optional[datetime] = None

state = AgentState()


class RunResult(BaseModel):
    success: bool
    message: str
    scraped_models: int = 0
    missing_models: int = 0
    pr_url: Optional[str] = None
    timestamp: str


class StatusResponse(BaseModel):
    status: str
    is_running: bool
    last_run: Optional[str]
    last_result: Optional[dict]
    next_scheduled_run: Optional[str]
    schedule_interval_hours: int = 24


async def run_agent() -> RunResult:
    """Run the full agent workflow."""
    if state.is_running:
        return RunResult(
            success=False,
            message="Agent is already running",
            timestamp=datetime.utcnow().isoformat(),
        )

    state.is_running = True
    start_time = datetime.utcnow()

    try:
        logger.info("=" * 60)
        logger.info("Starting Fireworks AI Cost Agent")
        logger.info("=" * 60)

        # Validate environment variables
        if not os.environ.get("FIRECRAWL_API_KEY"):
            raise ValueError("FIRECRAWL_API_KEY not set")
        if not os.environ.get("GITHUB_TOKEN"):
            raise ValueError("GITHUB_TOKEN not set")

        # Step 1: Scrape Fireworks AI models
        logger.info("📡 Scraping Fireworks AI models...")
        scraped_models = await scrape_fireworks_models()
        logger.info(f"   Found {len(scraped_models)} models")

        if not scraped_models:
            return RunResult(
                success=True,
                message="No models scraped from Fireworks AI",
                scraped_models=0,
                timestamp=start_time.isoformat(),
            )

        # Step 2: Fetch LiteLLM and compare
        logger.info("🔍 Comparing with LiteLLM database...")
        raw_content, litellm_data = await fetch_litellm_raw()
        logger.info(f"   LiteLLM has {len(litellm_data)} models")

        missing_models = compare_models(scraped_models, litellm_data)
        logger.info(f"   Missing models: {len(missing_models)}")

        if not missing_models:
            result = RunResult(
                success=True,
                message="All Fireworks models already exist in LiteLLM",
                scraped_models=len(scraped_models),
                missing_models=0,
                timestamp=start_time.isoformat(),
            )
            state.last_run = start_time
            state.last_result = result.model_dump()
            return result

        # Step 3: Create PR
        logger.info("🚀 Creating Pull Request...")
        pr_url = create_pull_request(
            missing_models=missing_models,
            original_json_content=raw_content,
        )

        result = RunResult(
            success=True,
            message=f"Created PR with {len(missing_models)} new models",
            scraped_models=len(scraped_models),
            missing_models=len(missing_models),
            pr_url=pr_url,
            timestamp=start_time.isoformat(),
        )

        logger.info(f"✅ PR created: {pr_url}")
        state.last_run = start_time
        state.last_result = result.model_dump()
        return result

    except Exception as e:
        logger.error(f"❌ Agent failed: {e}")
        result = RunResult(
            success=False,
            message=f"Agent failed: {str(e)}",
            timestamp=start_time.isoformat(),
        )
        state.last_run = start_time
        state.last_result = result.model_dump()
        return result

    finally:
        state.is_running = False


async def scheduled_run():
    """Wrapper for scheduled runs."""
    logger.info("⏰ Scheduled run triggered")
    await run_agent()
    # Update next scheduled run time
    state.next_scheduled_run = datetime.utcnow() + timedelta(hours=24)


@app.on_event("startup")
async def startup_event():
    """Start the scheduler on app startup."""
    # Schedule to run every 24 hours
    scheduler.add_job(
        scheduled_run,
        trigger=IntervalTrigger(hours=24),
        id="daily_sync",
        name="Daily Fireworks AI sync",
        replace_existing=True,
    )
    scheduler.start()
    state.next_scheduled_run = datetime.utcnow() + timedelta(hours=24)
    logger.info("🚀 Scheduler started - will run every 24 hours")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "Fireworks AI Cost Agent",
        "version": "1.0.0",
        "endpoints": {
            "/status": "Get agent status and schedule",
            "/trigger": "POST to trigger agent immediately",
            "/health": "Health check",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get agent status and next scheduled run."""
    return StatusResponse(
        status="running" if state.is_running else "idle",
        is_running=state.is_running,
        last_run=state.last_run.isoformat() if state.last_run else None,
        last_result=state.last_result,
        next_scheduled_run=state.next_scheduled_run.isoformat() if state.next_scheduled_run else None,
        schedule_interval_hours=24,
    )


@app.post("/trigger", response_model=RunResult)
async def trigger_agent(background_tasks: BackgroundTasks):
    """Trigger the agent to run immediately."""
    if state.is_running:
        raise HTTPException(
            status_code=409,
            detail="Agent is already running. Check /status for progress.",
        )

    # Run in background
    result = await run_agent()
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

