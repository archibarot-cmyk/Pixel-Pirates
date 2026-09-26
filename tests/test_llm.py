"""
Run this standalone to test the LLM layer in isolation, before touching QGIS.

Usage:
    python -m tests.test_llm
"""

from llm.llm_client import get_plan

TEST_QUERIES = [
    "Show vegetation loss in Pune between 2015 and 2020",
    "How much greenery has Pune lost since 2015?",
    "What does the vegetation health look like in Pune in 2020?",
    "What area in Pune is covered by dense vegetation in 2015?",
    "What's the weather like in Pune today?",          # should reject
    "Show me change detection for Mumbai 2018 to 2022",  # should reject (unsupported region/years)
]

if __name__ == "__main__":
    for query in TEST_QUERIES:
        plan = get_plan(query)
        status = "REJECTED" if plan["operation"] == "reject" else "OK"
        print(f"[{status}] \"{query}\"\n    -> {plan}\n")
