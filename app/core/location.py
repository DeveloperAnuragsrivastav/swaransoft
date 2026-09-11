"""
Handles 'where is your company located' style queries.
We intercept these with keyword matching BEFORE hitting the LLM,
so the address is always exact and never hallucinated.
"""
import re
from app.core.config import COMPANY_LOCATION

LOCATION_KEYWORDS = [
    "where", "location", "located", "address", "office",
    "how to reach", "find you", "situated", "map", "directions",
]


def is_location_query(message: str) -> bool:
    message = message.lower()
    return bool(re.search(r"\b(address|directions|located|headquarters)\b|where (?:are you|is (?:your|the) (?:company|office))|\b(?:office|company) location\b|\bhow (?:can i|to) (?:reach|find) you\b", message))


def get_location_response() -> dict:
    return {
        "type": "location",
        "text": (f"{COMPANY_LOCATION['name']} is located at: {COMPANY_LOCATION['address']}"
                 if COMPANY_LOCATION["address"] else
                 "Swaran Soft is headquartered in Gurugram, India. Please contact info@swaransoft.com for the current office address and directions."),
        "maps_link": COMPANY_LOCATION["maps_link"],
        "latitude": COMPANY_LOCATION["latitude"],
        "longitude": COMPANY_LOCATION["longitude"],
    }
