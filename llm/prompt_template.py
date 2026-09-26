"""
Prompt template for the NL -> JSON plan step.

Contract (agreed with the team):
    get_plan(query_text) -> {
        "operation": "ndvi" | "change_detection" | "area_extraction" | "reject",
        "region": "pune" | null,
        "year_1": 2015 | null,
        "year_2": 2020 | null,
        "reason": null | "<short reason, only when operation == 'reject'>"
    }

Only ONE region ("pune") and TWO years (2015, 2020) are supported for the demo.
The model must NEVER invent a 4th operation and must NEVER write code — only fill this schema.
"""

SYSTEM_PROMPT = """You are a strict query planner for a GIS tool. Your ONLY job is to read a
user's plain-English question and output a single JSON object matching this exact schema:

{
  "operation": "ndvi" | "change_detection" | "area_extraction" | "reject",
  "region": "pune" or null,
  "year_1": integer or null,
  "year_2": integer or null,
  "reason": string or null
}

Rules:
- Only "pune" is a supported region. Only 2015 and 2020 are supported years.
- If the question does not clearly map to one of the 3 supported operations, or asks about
  an unsupported region/year, or asks something unrelated to vegetation/land analysis,
  set "operation" to "reject" and give a short "reason".
- Output ONLY the JSON object. No markdown fences, no explanation, no extra text.
- Never invent a new operation name. Never leave "operation" out.

Supported operations:
- "ndvi": vegetation health/greenness for a single year.
- "change_detection": vegetation loss/gain between two years.
- "area_extraction": area (sq km) covered by vegetation above a threshold, for a single year.
"""

# 5 few-shot examples: NDVI, change_detection (x2, it's the headline demo), area_extraction, reject
FEW_SHOT_EXAMPLES = [
    {
        "query": "What does the vegetation health look like in Pune in 2020?",
        "plan": {
            "operation": "ndvi",
            "region": "pune",
            "year_1": 2020,
            "year_2": None,
            "reason": None
        }
    },
    {
        "query": "Show vegetation loss in Pune between 2015 and 2020",
        "plan": {
            "operation": "change_detection",
            "region": "pune",
            "year_1": 2015,
            "year_2": 2020,
            "reason": None
        }
    },
    {
        "query": "How much greenery has Pune lost since 2015?",
        "plan": {
            "operation": "change_detection",
            "region": "pune",
            "year_1": 2015,
            "year_2": 2020,
            "reason": None
        }
    },
    {
        "query": "What area in Pune is covered by dense vegetation in 2015?",
        "plan": {
            "operation": "area_extraction",
            "region": "pune",
            "year_1": 2015,
            "year_2": None,
            "reason": None
        }
    },
    {
        "query": "What's the population density of Mumbai in 2023?",
        "plan": {
            "operation": "reject",
            "region": None,
            "year_1": None,
            "year_2": None,
            "reason": "Unsupported region (Mumbai) and unsupported metric (population) — only Pune vegetation analysis for 2015/2020 is supported."
        }
    },
]


def build_prompt(query_text: str) -> str:
    """Assembles the final prompt sent to the LLM: system prompt + few-shots + the real query."""
    examples_text = "\n\n".join(
        f'User question: "{ex["query"]}"\nJSON: {_plan_to_json_str(ex["plan"])}'
        for ex in FEW_SHOT_EXAMPLES
    )
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Examples:\n{examples_text}\n\n"
        f'Now do the same for this question:\n'
        f'User question: "{query_text}"\nJSON:'
    )


def _plan_to_json_str(plan: dict) -> str:
    import json
    return json.dumps(plan)
