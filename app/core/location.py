"""
Handles 'where is your company located' style queries.
We intercept these with keyword matching BEFORE hitting the LLM,
so the address is always exact and never hallucinated.
"""
from app.core.config import COMPANY_LOCATION

LOCATION_KEYWORDS = [
    "where", "location", "located", "address", "office",
    "how to reach", "find you", "situated", "map", "directions",
]


def is_location_query(message: str) -> bool:
    message = message.lower()
    return any(keyword in message for keyword in LOCATION_KEYWORDS)


def get_location_response() -> dict:
    return {
        "type": "location",
        "text": f"{COMPANY_LOCATION['name']} is located at: {COMPANY_LOCATION['address']}",
        "maps_link": COMPANY_LOCATION["maps_link"],
        "latitude": COMPANY_LOCATION["latitude"],
        "longitude": COMPANY_LOCATION["longitude"],
    }
