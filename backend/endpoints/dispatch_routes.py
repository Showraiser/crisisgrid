from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.firestore_service import (
    get_dispatch_by_id,
    update_dispatch_route,
    get_all_zones,
    get_volunteer_by_team_name, 
    approve_dispatch,
)
from services.routes_service import call_routes_api_avoiding

router = APIRouter()


class BlockedPayload(BaseModel):
    blockedLat: float
    blockedLng: float


@router.post("/dispatch/{dispatchId}/blocked")
def handle_blocked_road(dispatchId: str, payload: BlockedPayload):
    """
    A field worker reports a road block on an active dispatch route.
    This endpoint recomputes the route, forcing a detour around the blocked point,
    and updates the dispatch document so Member 1's dashboard re-renders the polyline.
    """
    # 1. Fetch dispatch
    dispatch = get_dispatch_by_id(dispatchId)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    zone_id       = dispatch.get("zoneId")
    volunteer_team = dispatch.get("volunteerTeam")

    # 2. Get zone destination coordinates
    zones       = get_all_zones()
    target_zone = next((z for z in zones if z["id"] == zone_id), None)
    if not target_zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    dest_lat = target_zone["center"]["lat"]
    dest_lng = target_zone["center"]["lng"]

    # 3. Get volunteer origin coordinates (via service layer — no direct db here)
    volunteer = get_volunteer_by_team_name(volunteer_team)
    if not volunteer:
        raise HTTPException(status_code=404, detail=f"Volunteer team '{volunteer_team}' not found")

    origin_lat = volunteer["lat"]
    origin_lng = volunteer["lng"]

    # 4. Recompute route avoiding the blocked point
    try:
        new_polyline = call_routes_api_avoiding(
            origin_lat, origin_lng,
            dest_lat,   dest_lng,
            payload.blockedLat, payload.blockedLng,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route recomputation failed: {e}")

    # 5. Persist updated polyline + metadata
    now = datetime.utcnow()
    update_dispatch_route(
        dispatch_id    = dispatchId,
        new_polyline   = new_polyline,
        rerouted_at    = now,
        reroute_reason = "field_blocked_road",
    )

    return {
        "status":      "rerouted",
        "dispatchId":  dispatchId,
        "newPolyline": new_polyline,
        "reroutedAt":  now.isoformat(),
    }

class ApprovePayload(BaseModel):
    approvedBy: str


@router.patch("/dispatch/{dispatchId}/approve")
def approve_dispatch_route(dispatchId: str, payload: ApprovePayload):
    """
    Coordinator approves a pending dispatch from the dashboard.
    Sets status → approved and records who approved it.
    """
    dispatch = get_dispatch_by_id(dispatchId)
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    if dispatch.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Dispatch is already '{dispatch.get('status')}' — cannot approve."
        )

    approve_dispatch(dispatchId, payload.approvedBy)
    return {"status": "approved", "dispatchId": dispatchId, "approvedBy": payload.approvedBy}