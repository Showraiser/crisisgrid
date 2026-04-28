import math
import requests
from fastapi import HTTPException
from config import GOOGLE_MAPS_API_KEY

_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
_FIELD_MASK = "routes.polyline.encodedPolyline"


def _build_headers():
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY is not set.")
    return {
        "Content-Type":    "application/json",
        "X-Goog-Api-Key":  GOOGLE_MAPS_API_KEY.strip(),
        "X-Goog-FieldMask": _FIELD_MASK,
    }


def _compute_single_route(origin_lat, origin_lng, dest_lat, dest_lng, intermediates=None) -> str:
    """
    Calls Routes API v2. Returns encoded polyline string.
    Raises HTTPException on failure.
    """
    body = {
        "origin":      {"location": {"latLng": {"latitude": origin_lat,  "longitude": origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": dest_lat,    "longitude": dest_lng}}},
        "travelMode":  "DRIVE",
    }
    if intermediates:
        body["intermediates"] = intermediates

    resp = requests.post(_ROUTES_URL, headers=_build_headers(), json=body, timeout=10)
    print(f"Routes API request body: {body}")          
    print(f"Routes API response {resp.status_code}: {resp.text[:500]}")  
    if resp.status_code != 200:
        print(f"Routes API error {resp.status_code}: {resp.text}")
        raise HTTPException(status_code=500, detail="Routes API returned an error")

    try:
        return resp.json()["routes"][0]["polyline"]["encodedPolyline"]
    except (KeyError, IndexError) as e:
        raise HTTPException(status_code=500, detail=f"Unexpected Routes API response: {e}")


def call_routes_api(origin_lat: float, origin_lng: float,
                    dest_lat: float,   dest_lng: float) -> str:
    """Standard A→B route. Returns encoded polyline."""
    return _compute_single_route(origin_lat, origin_lng, dest_lat, dest_lng)


def call_routes_api_avoiding(origin_lat: float, origin_lng: float,
                              dest_lat: float,   dest_lng: float,
                              blocked_lat: float, blocked_lng: float) -> str:
    """
    Re-routes avoiding a blocked coordinate.

    Strategy: insert an intermediate waypoint that is offset ~1 km perpendicular
    to the direct origin→destination bearing, near the blocked point.
    This forces the Routes API to find a path that detours around the area.
    """
    # Compute bearing from origin to destination (degrees)
    d_lat = math.radians(dest_lat   - origin_lat)
    d_lng = math.radians(dest_lng   - origin_lng)
    bearing = math.degrees(math.atan2(d_lng, d_lat))

    # Perpendicular bearing (90° clockwise)
    perp_bearing = math.radians(bearing + 90)

    # Offset the blocked point ~0.012° (~1.3 km) perpendicular to route
    offset = 0.012
    detour_lat = blocked_lat + offset * math.cos(perp_bearing)
    detour_lng = blocked_lng + offset * math.sin(perp_bearing)

    intermediates = [{
        "location": {"latLng": {"latitude": detour_lat, "longitude": detour_lng}},
        "via": True,     # pass-through waypoint, not a stop
    }]

    print(f"Rerouting via detour waypoint ({detour_lat:.4f}, {detour_lng:.4f}) "
          f"to avoid blocked point ({blocked_lat}, {blocked_lng})")

    return _compute_single_route(origin_lat, origin_lng, dest_lat, dest_lng, intermediates)
