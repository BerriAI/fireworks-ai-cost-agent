"""Module for creating GitHub Pull Requests to add missing models."""

import json
import os
from datetime import datetime

from github import Github

from .browser_agent import FireworksModel

# Repository information
UPSTREAM_REPO = "BerriAI/litellm"
JSON_FILE_PATH = "model_prices_and_context_window.json"


def create_pull_request(
    missing_models: list[FireworksModel],
    original_json_content: str,
    github_token: str | None = None,
) -> str | None:
    """
    Create a Pull Request to add missing Fireworks models to LiteLLM.
    
    Uses append-only approach to preserve original file ordering.

    Args:
        missing_models: List of models to add
        original_json_content: The original JSON file content as string
        github_token: GitHub personal access token (uses GITHUB_TOKEN env var if not provided)

    Returns:
        URL of the created PR, or None if failed
    """
    token = github_token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    g = Github(token)
    user = g.get_user()
    repo = g.get_repo(UPSTREAM_REPO)

    # Create branch name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"add-fireworks-models-{timestamp}"

    # Get the default branch
    main_branch = repo.get_branch("main")

    # Create branch from main
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=main_branch.commit.sha,
    )

    # Build new entries and append to original content
    updated_content = append_models_to_json(missing_models, original_json_content)

    # Update the JSON file
    current_file = repo.get_contents(JSON_FILE_PATH, ref=branch_name)
    repo.update_file(
        path=JSON_FILE_PATH,
        message=f"Add {len(missing_models)} new Fireworks AI models",
        content=updated_content,
        sha=current_file.sha,
        branch=branch_name,
    )

    # Create the Pull Request
    pr_title = f"Add {len(missing_models)} new Fireworks AI models"
    pr_body = generate_pr_body(missing_models)

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base="main",
    )

    return pr.html_url


def append_models_to_json(
    models: list[FireworksModel], original_content: str
) -> str:
    """
    Append new models to the JSON content without reordering existing entries.
    
    This preserves the original file structure and only adds new entries at the end.
    """
    # Build new entries
    new_entries = {}
    for m in models:
        key = f"fireworks_ai/accounts/fireworks/models/{m.model_id}"
        new_entries[key] = m.to_litellm_format()

    # Convert new entries to JSON string (without outer braces)
    new_entries_str = json.dumps(new_entries, indent=4)[1:-1]

    # Find position of last closing brace
    last_brace = original_content.rfind("}")

    # Check if there's content before the last brace (need comma)
    content_before = original_content[:last_brace].rstrip()
    if content_before.endswith("}"):
        # Need to add a comma after the last entry
        updated_content = content_before + "," + new_entries_str + "\n}"
    else:
        updated_content = content_before + new_entries_str + "\n}"

    # Validate the JSON
    json.loads(updated_content)  # Raises if invalid

    return updated_content


def generate_pr_body(missing_models: list[FireworksModel]) -> str:
    """Generate the PR description body."""
    # Build model list (first 50)
    model_list = "\n".join(
        f"- `fireworks_ai/accounts/fireworks/models/{m.model_id}`"
        for m in missing_models[:50]
    )

    if len(missing_models) > 50:
        model_list += f"\n- ... and {len(missing_models) - 50} more models"

    # Group by mode/type
    types = {}
    for m in missing_models:
        mode = m.to_litellm_format().get("mode", "chat")
        types[mode] = types.get(mode, 0) + 1

    type_summary = ", ".join(f"{count} {t}" for t, count in sorted(types.items()))

    body = f"""## Summary

This PR adds **{len(missing_models)} new Fireworks AI models** to the LiteLLM model pricing database.

### Model Types Added
{type_summary}

### Models Added

{model_list}

---

### Source
Models scraped from https://fireworks.ai/models

### Verification
Please verify the pricing information is accurate by checking https://fireworks.ai/models
"""
    return body


if __name__ == "__main__":
    # Test generating PR body
    test_models = [
        FireworksModel(
            name="Test Model 1",
            model_id="test-model-1",
            input_cost_per_million=0.5,
            output_cost_per_million=1.0,
            unified_cost_per_million=None,
            context_window=32768,
            model_type="LLM",
        ),
        FireworksModel(
            name="Test Model 2",
            model_id="test-model-2",
            input_cost_per_million=None,
            output_cost_per_million=None,
            unified_cost_per_million=0.2,
            context_window=4096,
            model_type="Vision",
        ),
    ]

    print(generate_pr_body(test_models))
