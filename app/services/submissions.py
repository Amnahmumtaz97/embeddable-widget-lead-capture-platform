import re
from typing import Any

from fastapi import HTTPException

from app.models import SubmissionCreate


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_submission_data(widget: dict[str, Any], submission: SubmissionCreate) -> dict[str, str]:
    configured = {field["name"]: field for field in widget["form_fields"]}
    unexpected = sorted(set(submission.data) - set(configured))
    if unexpected:
        raise HTTPException(422, detail={"error": "Unexpected fields", "fields": unexpected})

    errors: dict[str, str] = {}
    cleaned: dict[str, str] = {}
    for name, field in configured.items():
        value = submission.data.get(name, "").strip()
        if field.get("required", True) and not value:
            errors[name] = "This field is required"
            continue
        if len(value) > int(field.get("max_length", 255)):
            errors[name] = "This field is too long"
            continue
        if value and field.get("type") == "email" and not EMAIL_RE.match(value):
            errors[name] = "Enter a valid email address"
            continue
        if value:
            cleaned[name] = value
    if errors:
        raise HTTPException(422, detail={"error": "Submission validation failed", "fields": errors})
    return cleaned
