from fastapi import APIRouter
from app.core.location import get_location_response

router = APIRouter()


@router.get("/location")
async def location():
    """Direct endpoint to fetch company location (used by a 'Find us' button in the UI)."""
    return get_location_response()
