import json
from typing import Any


def validate_event_body(event_body: str):
    try:
        return json.loads(event_body)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format for event body")


def validate_trackers(trackers: Any) -> list[str]:
    if isinstance(trackers, list) and all(isinstance(tracker, str) for tracker in trackers):
        return trackers
    return []


def is_mp3_url(url: str) -> bool:
    # Check if the URL ends with .mp3
    # This is a simple check and is not cover all cases
    # Added for demonstration purposes
    # Additional checks can be added
    return url.lower().endswith(".mp3")
