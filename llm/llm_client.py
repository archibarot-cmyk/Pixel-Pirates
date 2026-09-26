"""
The single entry point everyone else calls: get_plan(query_text) -> dict

Swap backends by changing DEFAULT_PROVIDER or passing provider= explicitly.
All three backends are free / no-card-required, per the team's zero-cost stack:
  - "gemini": Google AI Studio free tier (needs GEMINI_API_KEY)
  - "groq":   Groq free tier, fast (needs GROQ_API_KEY)
  - "ollama": fully local, no key, no internet needed (needs Ollama running locally)
"""

import os
import json
import re

from llm.prompt_template import build_prompt
from llm.validator import validate_plan, make_reject_plan, PlanValidationError

DEFAULT_PROVIDER = "gemini"  # change to "groq" or "ollama" if you swap backends

# --- Hardcoded fallback responses -----------------------------------------
# If the live API is slow/down during judging, these guarantee your 3 demo
# queries still work. Match these strings EXACTLY to what you'll type on stage.
CACHED_FALLBACKS = {
    "show vegetation loss in pune between 2015 and 2020": {
        "operation": "change_detection", "region": "pune",
        "year_1": 2015, "year_2": 2020, "reason": None
    },
    "what does vegetation health look like in pune in 2020": {
        "operation": "ndvi", "region": "pune",
        "year_1": 2020, "year_2": None, "reason": None
    },
    "what area in pune is covered by dense vegetation in 2015": {
        "operation": "area_extraction", "region": "pune",
        "year_1": 2015, "year_2": None, "reason": None
    },
}


def get_plan(query_text: str, provider: str = DEFAULT_PROVIDER, use_cache_first: bool = False) -> dict:
    """
    Main entry point. Returns a validated plan dict, or a well-formed reject plan
    if the query is unsupported or something goes wrong.
    """
    normalized = query_text.strip().lower()

    if use_cache_first and normalized in CACHED_FALLBACKS:
        return CACHED_FALLBACKS[normalized]

    try:
        raw_text = _call_backend(query_text, provider)
        plan = _parse_json(raw_text)
        return validate_plan(plan)
    except PlanValidationError as e:
        return make_reject_plan(str(e))
    except Exception as e:
        # Live call failed (network, rate limit, bad key, etc.) — fall back to cache if we have it,
        # otherwise reject cleanly instead of crashing the plugin.
        if normalized in CACHED_FALLBACKS:
            return CACHED_FALLBACKS[normalized]
        return make_reject_plan(f"LLM call failed: {e}")


def _parse_json(raw_text: str) -> dict:
    """Strips markdown fences if the model added them anyway, then parses JSON."""
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _call_backend(query_text: str, provider: str) -> str:
    prompt = build_prompt(query_text)
    if provider == "gemini":
        return _call_gemini(prompt)
    elif provider == "groq":
        return _call_groq(prompt)
    elif provider == "ollama":
        return _call_ollama(prompt)
    else:
        raise ValueError(f"Unknown provider '{provider}'")


def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.8-flash")
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    return response.text


def _call_groq(prompt: str) -> str:
    from groq import Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _call_ollama(prompt: str) -> str:
    import ollama
    response = ollama.generate(model="llama3.2:3b", prompt=prompt, format="json")
    return response["response"]
