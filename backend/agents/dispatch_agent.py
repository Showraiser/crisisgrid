"""
Dispatch Agent — ADK LlmAgent that finds the nearest volunteer, computes the
route via Google Maps Routes API, and writes a dispatch document to Firestore.
"""
from google.adk.agents import LlmAgent
from config import GEMINI_MODEL_FLASH
from services.firestore_service import (
    get_all_zones,
    get_nearest_available_volunteer,
    write_dispatch,
)
from services.routes_service import call_routes_api


# ── Tool functions ────────────────────────────────────────────────────────────

def fetch_target_zone(zone_id: str) -> dict:
    """Return the full zone document for a given zone_id."""
    zones = get_all_zones()
    zone  = next((z for z in zones if z["id"] == zone_id), None)
    if not zone:
        return {"error": f"Zone {zone_id} not found"}
    return zone


def fetch_nearest_volunteer(dest_lat: float, dest_lng: float) -> dict:
    """Return the nearest available volunteer team to the target coordinates."""
    volunteer = get_nearest_available_volunteer(dest_lat, dest_lng)
    if not volunteer:
        return {"error": "No available volunteers"}
    return volunteer


def compute_route_and_dispatch(
    volunteer_team: str,
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    zone_id: str,
    ai_reason: str,
    confidence: float,
) -> dict:
    """Compute the driving route and write the dispatch document."""
    polyline    = call_routes_api(origin_lat, origin_lng, dest_lat, dest_lng)
    dispatch_id = write_dispatch(
        volunteer_team  = volunteer_team,
        zone_id         = zone_id,
        route_polyline  = polyline,
        ai_reason       = ai_reason,
        confidence      = confidence,
        status          = "pending",
    )
    return {"dispatch_id": dispatch_id, "polyline_length": len(polyline)}


# ── ADK Agent definition ──────────────────────────────────────────────────────
dispatch_agent = LlmAgent(
    name        = "dispatch_agent",
    model       = GEMINI_MODEL_FLASH,
    description = "Assigns the nearest volunteer to a target zone and writes a dispatch.",
    instruction = (
        "You are the Dispatch Agent for CrisisGrid. "
        "Given a targetZoneId, reason, and confidence from context, "
        "call fetch_target_zone to get zone coordinates, "
        "then fetch_nearest_volunteer with those coordinates, "
        "then compute_route_and_dispatch with all collected data. "
        "Return the dispatch_id."
    ),
    tools = [fetch_target_zone, fetch_nearest_volunteer, compute_route_and_dispatch],
)


# ── Convenience wrapper ───────────────────────────────────────────────────────
class DispatchAgent:

    def run(self, context: dict) -> dict | None:
        print("Dispatch Agent: preparing dispatch...")

        target_id  = context.get("targetZoneId")
        reason     = context.get("reason", "")
        confidence = context.get("confidence", 0.8)

        if not target_id:
            print("Dispatch Agent: no targetZoneId provided.")
            return None

        zones  = get_all_zones()
        zone   = next((z for z in zones if z["id"] == target_id), None)
        if not zone:
            print(f"Dispatch Agent: zone {target_id} not found.")
            return None

        dest_lat = zone["center"]["lat"]
        dest_lng = zone["center"]["lng"]

        volunteer = get_nearest_available_volunteer(dest_lat, dest_lng)
        if not volunteer:
            print("Dispatch Agent: no available volunteers.")
            return None

        try:
            polyline = call_routes_api(volunteer["lat"], volunteer["lng"], dest_lat, dest_lng)
        except Exception as e:
            print(f"Dispatch Agent: Routes API failed: {e}")
            return None

        dispatch_id = write_dispatch(
            volunteer_team = volunteer["teamName"],
            zone_id        = target_id,
            route_polyline = polyline,
            ai_reason      = reason,
            confidence     = confidence,
            status         = "pending",
        )
        print(f"Dispatch Agent: created dispatch {dispatch_id} for {volunteer['teamName']} → {target_id}")
        return {"dispatch_id": dispatch_id}
