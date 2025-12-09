"""Module for comparing scraped models against LiteLLM database."""

import json

import httpx

from .browser_agent import FireworksModel

# LiteLLM model prices JSON raw URL
LITELLM_JSON_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"


async def fetch_litellm_models() -> dict:
    """
    Fetch the current model_prices_and_context_window.json from LiteLLM GitHub.

    Returns the parsed JSON as a dictionary.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(LITELLM_JSON_URL, timeout=30.0)
        response.raise_for_status()
        return response.json()


def get_fireworks_models_from_litellm(litellm_data: dict) -> set[str]:
    """
    Extract all Fireworks AI model IDs from LiteLLM data.

    Returns a set of model IDs (without the 'fireworks_ai/' prefix).
    """
    fireworks_models = set()

    for key in litellm_data.keys():
        if key.startswith("fireworks_ai/"):
            # Remove the prefix to get just the model ID
            model_id = key.replace("fireworks_ai/", "")
            fireworks_models.add(model_id)

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
        # Check if this model exists in LiteLLM
        # We try multiple variations of the model ID
        model_id_variations = [
            model.model_id,
            model.model_id.replace("-", "_"),
            model.model_id.replace("_", "-"),
            model.name.lower().replace(" ", "-"),
            model.name.lower().replace(" ", "_"),
        ]

        found = False
        for variation in model_id_variations:
            if variation in existing_ids:
                found = True
                break

        if not found:
            missing_models.append(model)

    return missing_models


def generate_litellm_json_update(
    missing_models: list[FireworksModel], existing_data: dict
) -> dict:
    """
    Generate the updated LiteLLM JSON with new models added.

    Returns the complete updated dictionary.
    """
    updated_data = existing_data.copy()

    for model in missing_models:
        key = f"fireworks_ai/{model.model_id}"
        updated_data[key] = model.to_litellm_format()

    return updated_data


def generate_json_diff(
    missing_models: list[FireworksModel],
) -> str:
    """
    Generate a JSON snippet showing just the new models to be added.

    Useful for PR descriptions.
    """
    new_entries = {}
    for model in missing_models:
        key = f"fireworks_ai/{model.model_id}"
        new_entries[key] = model.to_litellm_format()

    return json.dumps(new_entries, indent=2)


if __name__ == "__main__":
    import asyncio

    async def test():
        print("Fetching LiteLLM models...")
        litellm_data = await fetch_litellm_models()
        print(f"Total models in LiteLLM: {len(litellm_data)}")

        fireworks_ids = get_fireworks_models_from_litellm(litellm_data)
        print(f"Existing Fireworks models: {len(fireworks_ids)}")
        for mid in sorted(fireworks_ids)[:10]:
            print(f"  - {mid}")

    asyncio.run(test())

