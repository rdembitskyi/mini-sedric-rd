import json
from typing import Any


def validate_trackers(raw_trackers: Any) -> list[str]:
    if isinstance(raw_trackers, str):
        try:
            trackers = json.loads(raw_trackers)
            if isinstance(trackers, list):
                return trackers
        except json.JSONDecodeError:
            print("Invalid JSON format for trackers")
            return []

    return raw_trackers if isinstance(raw_trackers, list) else []


def is_mp3_url(url: str) -> bool:
    # Check if the URL ends with .mp3
    # This is a simple check and is not cover all cases
    # Added for demonstration purposes
    # Additional checks can be added
    return url.lower().endswith(".mp3")
