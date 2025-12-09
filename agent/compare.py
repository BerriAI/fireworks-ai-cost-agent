"""Module for comparing scraped models against LiteLLM database."""

import json

import httpx

from .browser_agent import FireworksModel

# LiteLLM model prices JSON raw URL
LITELLM_JSON_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"


async def fetch_litellm_raw() -> tuple[str, dict]:
    """
    Fetch the current model_prices_and_context_window.json from LiteLLM GitHub.

    Returns tuple of (raw_content_string, parsed_dict).
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(LITELLM_JSON_URL, timeout=30.0)
        response.raise_for_status()
        raw_content = response.text
        return raw_content, json.loads(raw_content)


async def fetch_litellm_models() -> dict:
    """
    Fetch the current model_prices_and_context_window.json from LiteLLM GitHub.

    Returns the parsed JSON as a dictionary.
    """
    _, data = await fetch_litellm_raw()
    return data


def normalize_model_id(model_id: str) -> str:
    """Normalize model ID for comparison."""
    # Remove common prefixes
    id = model_id.replace("accounts/fireworks/models/", "")
    return id.lower().strip()


def get_fireworks_models_from_litellm(litellm_data: dict) -> set[str]:
    """
    Extract all Fireworks AI model IDs from LiteLLM data.

    Returns a set of normalized model IDs.
    """
    fireworks_models = set()

    for key in litellm_data.keys():
        if key.startswith("fireworks_ai/"):
            # Remove the prefix to get just the model ID
            model_id = key.replace("fireworks_ai/", "")
            fireworks_models.add(normalize_model_id(model_id))

    return fireworks_models


def compare_models(
    scraped_models: list[FireworksModel], litellm_data: dict
) -> list[FireworksModel]:
    """
    Compare scraped models against LiteLLM database.

    Returns a list of models that are missing from LiteLLM.
    """
    existing_ids = get_fireworks_models_from_litellm(litellm_data)

    missing_models = []
    for model in scraped_models:
        # Normalize the model ID for comparison
        normalized = normalize_model_id(model.model_id)
        
        if normalized not in existing_ids:
            missing_models.append(model)

    return missing_models


def generate_json_diff(
    missing_models: list[FireworksModel],
) -> str:
    """
    Generate a JSON snippet showing just the new models to be added.

    Useful for PR descriptions and debugging.
    """
    new_entries = {}
    for model in missing_models:
        key = f"fireworks_ai/accounts/fireworks/models/{model.model_id}"
        new_entries[key] = model.to_litellm_format()

    return json.dumps(new_entries, indent=2)


if __name__ == "__main__":
    import asyncio

    async def test():
        print("Fetching LiteLLM models...")
        raw, litellm_data = await fetch_litellm_raw()
        print(f"Total models in LiteLLM: {len(litellm_data)}")
        print(f"Raw content length: {len(raw)} chars")

        fireworks_ids = get_fireworks_models_from_litellm(litellm_data)
        print(f"Existing Fireworks models: {len(fireworks_ids)}")
        for mid in sorted(fireworks_ids)[:10]:
            print(f"  - {mid}")

    asyncio.run(test())
