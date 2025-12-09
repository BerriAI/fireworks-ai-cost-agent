"""Browser agent module for scraping Fireworks AI models using Firecrawl."""

import os
import re
from dataclasses import dataclass

import httpx


@dataclass
class FireworksModel:
    """Represents a Fireworks AI model with pricing information."""

    name: str
    model_id: str
    input_cost_per_million: float | None
    output_cost_per_million: float | None
    unified_cost_per_million: float | None  # When input/output have same price
    context_window: int | None
    model_type: str  # LLM, Vision, Image, Audio, Embedding, Reranker

    def to_litellm_format(self) -> dict:
        """Convert to LiteLLM JSON format."""
        # Convert $/M tokens to $/token (round to avoid floating point noise)
        if self.unified_cost_per_million is not None:
            input_cost = round(self.unified_cost_per_million / 1_000_000, 12)
            output_cost = round(self.unified_cost_per_million / 1_000_000, 12)
        else:
            input_cost = (
                round(self.input_cost_per_million / 1_000_000, 12)
                if self.input_cost_per_million
                else 0
            )
            output_cost = (
                round(self.output_cost_per_million / 1_000_000, 12)
                if self.output_cost_per_million
                else 0
            )

        # Determine mode based on model type
        mode_map = {
            "LLM": "chat",
            "Vision": "chat",
            "Image": "image_generation",
            "Audio": "audio_transcription",
            "Embedding": "embedding",
            "Reranker": "rerank",
        }
        mode = mode_map.get(self.model_type, "chat")
        
        # Override mode based on model name keywords (Fireworks sometimes mislabels these)
        name_lower = self.name.lower()
        id_lower = self.model_id.lower()
        if "rerank" in name_lower or "rerank" in id_lower:
            mode = "rerank"
        elif "embed" in name_lower or "embed" in id_lower:
            mode = "embedding"
        elif "whisper" in name_lower or "asr" in id_lower:
            mode = "audio_transcription"

        result = {
            "max_tokens": self.context_window or 4096,
            "max_input_tokens": self.context_window or 4096,
            "max_output_tokens": self.context_window or 4096,
            "input_cost_per_token": input_cost,
            "output_cost_per_token": output_cost,
            "litellm_provider": "fireworks_ai",
            "mode": mode,
        }

        return result


def parse_pricing(pricing_text: str) -> tuple[float | None, float | None, float | None, int | None]:
    """
    Parse pricing text and return (input_cost, output_cost, unified_cost, context_window).
    
    Examples:
    - "$0.45/M Input • $1.8/M Output • 262144 Context" -> (0.45, 1.8, None, 262144)
    - "$0.2/M Tokens • 4096 Context" -> (None, None, 0.2, 4096)
    - "$0.04/Image" -> (None, None, 0.04, None)
    """
    input_cost = None
    output_cost = None
    unified_cost = None
    context_window = None
    
    # Try input/output pricing pattern
    io_match = re.search(r"\$([0-9.]+)/M\s*Input\s*[•·]\s*\$([0-9.]+)/M\s*Output", pricing_text)
    if io_match:
        input_cost = float(io_match.group(1))
        output_cost = float(io_match.group(2))
    else:
        # Try unified tokens pricing pattern
        tokens_match = re.search(r"\$([0-9.]+)/M\s*Tokens?", pricing_text)
        if tokens_match:
            unified_cost = float(tokens_match.group(1))
        else:
            # Try per-image pricing
            image_match = re.search(r"\$([0-9.]+)/Image", pricing_text)
            if image_match:
                unified_cost = float(image_match.group(1))
            else:
                # Try per-step pricing
                step_match = re.search(r"\$([0-9.]+)/Step", pricing_text)
                if step_match:
                    unified_cost = float(step_match.group(1))
    
    # Extract context window
    context_match = re.search(r"(\d+)\s*Context", pricing_text)
    if context_match:
        context_window = int(context_match.group(1))
    
    return input_cost, output_cost, unified_cost, context_window


def extract_model_id_from_url(url: str) -> str:
    """Extract model ID from URL like /models/fireworks/model-name."""
    match = re.search(r"/models/[^/]+/([^/\)]+)", url)
    if match:
        return match.group(1)
    return ""


def parse_firecrawl_markdown(markdown: str) -> list[FireworksModel]:
    """
    Parse the Firecrawl markdown output to extract model information.
    
    Each model follows this pattern in markdown:
    **Model Name**\\n\\n$pricing\\n\\nType](https://fireworks.ai/models/fireworks/model-id)
    """
    models = []
    
    # Pattern to match model entries
    # Matches: **Name**\n\n$pricing\n\nType](url)
    pattern = r'\*\*([^*]+)\*\*[\\n\s]*([^\\]*(?:\$[^\\]+))[\\n\s]*(LLM|Vision|Image|Audio|Embedding|Reranker)?\]?\(?(https://fireworks\.ai/models/[^)\s]+)'
    
    matches = re.findall(pattern, markdown)
    
    for match in matches:
        name = match[0].strip()
        pricing_text = match[1].strip()
        model_type = match[2].strip() if match[2] else "LLM"
        url = match[3].strip()
        
        # Extract model ID from URL
        model_id = extract_model_id_from_url(url)
        if not model_id:
            continue
        
        # Parse pricing
        input_cost, output_cost, unified_cost, context_window = parse_pricing(pricing_text)
        
        model = FireworksModel(
            name=name,
            model_id=model_id,
            input_cost_per_million=input_cost,
            output_cost_per_million=output_cost,
            unified_cost_per_million=unified_cost,
            context_window=context_window,
            model_type=model_type,
        )
        models.append(model)
    
    # Deduplicate by model_id
    seen_ids = set()
    unique_models = []
    for m in models:
        if m.model_id not in seen_ids:
            seen_ids.add(m.model_id)
            unique_models.append(m)
    
    return unique_models


async def scrape_fireworks_models() -> list[FireworksModel]:
    """
    Use Firecrawl API to scrape all models from Fireworks AI.
    
    Returns a list of FireworksModel objects with pricing information.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY environment variable is required")
    
    print("Fetching Fireworks AI models page via Firecrawl...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.firecrawl.dev/v2/scrape",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "url": "https://fireworks.ai/models",
                "onlyMainContent": False,
                "formats": ["markdown"],
            },
        )
        response.raise_for_status()
        data = response.json()
    
    if not data.get("success"):
        raise RuntimeError(f"Firecrawl API error: {data}")
    
    markdown = data.get("data", {}).get("markdown", "")
    if not markdown:
        raise RuntimeError("No markdown content returned from Firecrawl")
    
    print(f"Received {len(markdown)} characters of markdown content")
    
    # Parse the markdown
    models = parse_firecrawl_markdown(markdown)
    
    print(f"Successfully extracted {len(models)} unique models")
    return models


def run_scraper() -> list[FireworksModel]:
    """Synchronous wrapper to run the async scraper."""
    import asyncio
    return asyncio.run(scrape_fireworks_models())


if __name__ == "__main__":
    # Test the scraper
    models = run_scraper()
    print(f"\nFound {len(models)} models:")
    for model in models[:15]:  # Print first 15
        pricing = ""
        if model.input_cost_per_million:
            pricing = f"${model.input_cost_per_million}/M in, ${model.output_cost_per_million}/M out"
        elif model.unified_cost_per_million:
            pricing = f"${model.unified_cost_per_million}/M"
        print(f"  - {model.name} | {model.model_id} | {model.model_type} | {pricing}")
