import asyncio
import requests
import json
from typing import Dict, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:latest"

# ------------------------------------------------------------------
# Web research helpers (RAG layer)
# ------------------------------------------------------------------

def _ddg_search(query: str, max_results: int = 3) -> str:
    """
    Fetches plain-text search snippets from DuckDuckGo HTML search.
    No API key required.  Returns a combined string of snippets.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        snippets = []
        for result in soup.select(".result__snippet")[:max_results]:
            snippets.append(result.get_text(strip=True))
        return " | ".join(snippets) if snippets else ""
    except Exception as e:
        return f"[web search failed: {e}]"


def research_brand(brand: str) -> str:
    """
    Searches for cruelty-free and vegan certification status of a brand.
    Returns a short paragraph of web-sourced context.
    """
    if not brand:
        return ""
    snippets = []

    # 1. Cruelty-free / PETA / Leaping Bunny status
    q1 = f'"{brand}" cruelty-free vegan certified PETA Leaping Bunny'
    s1 = _ddg_search(q1)
    if s1:
        snippets.append(f"Cruelty-free info: {s1}")

    # 2. Parent company animal testing policies
    q2 = f'"{brand}" parent company animal testing policy China'
    s2 = _ddg_search(q2, max_results=2)
    if s2:
        snippets.append(f"Parent company policy: {s2}")

    # 3. Labor/supply chain
    q3 = f'"{brand}" supply chain labor practices ethical fair trade'
    s3 = _ddg_search(q3, max_results=2)
    if s3:
        snippets.append(f"Supply chain: {s3}")

    return "\n".join(snippets)


def research_ingredients(ingredients: str) -> str:
    """
    Looks up whether notable ingredients listed are vegan.
    Only runs a search if there are non-trivial ingredients.
    """
    if not ingredients or len(ingredients) < 20:
        return ""
    # Take first 200 chars of ingredients for the search query
    short_query = ingredients[:200].replace("\n", " ").strip()
    query = f"Are these ingredients vegan: {short_query[:120]}"
    result = _ddg_search(query, max_results=2)
    return f"Ingredient vegan status: {result}" if result else ""


# ------------------------------------------------------------------
# Main evaluator
# ------------------------------------------------------------------

async def evaluate_product(product_metadata: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    """
    Sends structured product metadata and a prompt to a local Ollama instance.
    Before calling the model, fetches real-time web context about the brand
    and ingredients to minimise null / uncertain answers.
    """
    brand = product_metadata.get("brand", "")
    ingredients = product_metadata.get("ingredients", product_metadata.get("materials", ""))

    # ------ RAG: gather web context --------------------------------
    def gather_context():
        ctx_parts = []
        brand_ctx = research_brand(brand)
        if brand_ctx:
            ctx_parts.append(brand_ctx)
        ing_ctx = research_ingredients(ingredients)
        if ing_ctx:
            ctx_parts.append(ing_ctx)
        return "\n\n".join(ctx_parts)

    try:
        web_context = await asyncio.to_thread(gather_context)
    except Exception:
        web_context = ""

    # ------ Build the prompt ---------------------------------------
    system_prompt = (
        "You are an expert AI evaluator assessing products for vegan status and ethical practices. "
        "You MUST output ONLY a raw JSON object and absolutely nothing else — no preamble, no thinking "
        "tags, no markdown code fences (no ```json). "
        "The JSON MUST contain exactly these four keys with NO null values: "
        "\"is_vegan\" (boolean), \"company_cruelty_free\" (boolean), "
        "\"supply_chain_ethical\" (boolean), and \"detailed_explanation\" (string — be specific, "
        "cite brand names or ingredients found in the web context). "
        "If you are uncertain, make your best-informed judgement and explain your reasoning in "
        "detailed_explanation. Never return null for boolean fields — default to false if unsure."
    )

    web_section = (
        f"\n\n=== WEB RESEARCH CONTEXT ===\n{web_context}\n=== END WEB CONTEXT ===\n"
        if web_context
        else ""
    )

    combined_prompt = (
        f"Product Metadata:\n{json.dumps(product_metadata, indent=2)}"
        f"{web_section}"
        f"\n\nTask:\n{prompt}"
        "\n\nIMPORTANT: Return ONLY the raw JSON object with the four required keys. "
        "No thinking process, no markdown, just the JSON."
    )

    payload = {
        "model": MODEL_NAME,
        "prompt": combined_prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json"
    }

    def make_request():
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()

    try:
        data = await asyncio.to_thread(make_request)
        response_text = data.get("response", "{}").strip()

        # Strip any accidental markdown fencing or <think> tags
        import re
        response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL)
        response_text = re.sub(r"```json\s*", "", response_text)
        response_text = re.sub(r"```\s*", "", response_text)
        response_text = response_text.strip()

        # Sometimes the model wraps in outer object — find first valid JSON object
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            response_text = match.group(0)

        result = json.loads(response_text)

        # Ensure all required keys are present and not null
        defaults = {
            "is_vegan": False,
            "company_cruelty_free": False,
            "supply_chain_ethical": False,
            "detailed_explanation": "No explanation provided."
        }
        for key, default in defaults.items():
            if key not in result or result[key] is None:
                result[key] = default

        # Coerce booleans in case the model returned strings
        for key in ["is_vegan", "company_cruelty_free", "supply_chain_ethical"]:
            val = result[key]
            if isinstance(val, str):
                result[key] = val.lower() in ("true", "yes", "1")

        return result

    except Exception as e:
        print(f"Error evaluating product with AI: {e}")
        return {
            "is_vegan": False,
            "company_cruelty_free": False,
            "supply_chain_ethical": False,
            "detailed_explanation": f"AI evaluation failed: {str(e)}"
        }


if __name__ == "__main__":
    test_meta = {
        "brand": "e.l.f. Cosmetics",
        "title": "e.l.f. SKIN Holy Hydration Makeup Remover",
        "ingredients": "Water, Hyaluronic Acid, Squalane, Niacinamide"
    }
    test_prompt = "Please evaluate if this cosmetic product is vegan and cruelty-free."
    result = asyncio.run(evaluate_product(test_meta, test_prompt))
    print(json.dumps(result, indent=2))
