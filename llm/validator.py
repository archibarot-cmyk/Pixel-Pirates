"""
Validates a plan dict returned by the LLM before it's ever handed to the engine functions.
This is what makes "reject unsupported queries with a clear error" actually happen.
"""

SUPPORTED_OPERATIONS = {"ndvi", "change_detection", "area_extraction", "reject"}
SUPPORTED_REGIONS = {"pune"}
SUPPORTED_YEARS = {2015, 2020}


class PlanValidationError(Exception):
    """Raised when a plan is malformed or asks for something outside the supported scope."""
    pass


def validate_plan(plan: dict) -> dict:
    """
    Raises PlanValidationError with a clear, user-facing message if the plan is invalid.
    Returns the plan unchanged if it's valid.
    """
    if not isinstance(plan, dict):
        raise PlanValidationError("Model did not return a JSON object.")

    operation = plan.get("operation")
    if operation not in SUPPORTED_OPERATIONS:
        raise PlanValidationError(
            f"Unsupported operation '{operation}'. Only ndvi, change_detection, "
            f"area_extraction are supported."
        )

    if operation == "reject":
        # A reject plan is always "valid" — it's the model's way of saying "can't do this."
        return plan

    region = plan.get("region")
    if region not in SUPPORTED_REGIONS:
        raise PlanValidationError(
            f"Unsupported region '{region}'. Only 'pune' is supported in this demo."
        )

    year_1 = plan.get("year_1")
    year_2 = plan.get("year_2")

    if operation in ("ndvi", "area_extraction"):
        if year_1 not in SUPPORTED_YEARS:
            raise PlanValidationError(
                f"Unsupported year '{year_1}'. Only 2015 and 2020 are supported."
            )

    if operation == "change_detection":
        if year_1 not in SUPPORTED_YEARS or year_2 not in SUPPORTED_YEARS:
            raise PlanValidationError(
                f"change_detection needs two supported years (2015, 2020), got "
                f"year_1={year_1}, year_2={year_2}."
            )
        if year_1 == year_2:
            raise PlanValidationError("change_detection needs two different years.")

    return plan


def make_reject_plan(reason: str) -> dict:
    """Helper to build a well-formed reject plan, e.g. when JSON parsing fails entirely."""
    return {
        "operation": "reject",
        "region": None,
        "year_1": None,
        "year_2": None,
        "reason": reason,
    }
