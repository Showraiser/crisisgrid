import math
from datetime import datetime
from fastapi import HTTPException
from google.cloud import firestore as google_firestore
from config import db


# ── Haversine distance (km) ─────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dLon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Reports ─────────────────────────────────────────────────────────────────
def get_report_by_id(report_id: str):
    try:
        doc = db.collection("reports").document(report_id).get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None
    except Exception as e:
        print(f"Error fetching report {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch report from Firestore")


def get_unprocessed_reports():
    try:
        reports_ref = (db.collection("reports")
                         .order_by("timestamp", direction="DESCENDING")
                         .limit(100))
        reports = []
        for doc in reports_ref.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            reports.append(data)

        if not reports:
            return []

        report_ids = [r["id"] for r in reports]
        processed_ids = set()
        for i in range(0, len(report_ids), 30):
            chunk = report_ids[i : i + 30]
            for doc in db.collection("processedReports").where("reportId", "in", chunk).stream():
                processed_ids.add(doc.to_dict().get("reportId"))

        return [r for r in reports if r["id"] not in processed_ids]
    except Exception as e:
        print(f"Error fetching unprocessed reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch unprocessed reports")


# ── Zone upsert (atomic transaction) ────────────────────────────────────────
@google_firestore.transactional
def _update_zone_tx(transaction, zone_ref, lat, lng, severity):
    snapshot = zone_ref.get(transaction=transaction)
    if snapshot.exists:
        data      = snapshot.to_dict()
        old_count = data.get("reportCount", 0)
        old_sev   = data.get("severity", 0.0)
        new_count = old_count + 1
        new_sev   = ((old_sev * old_count) + severity) / new_count
        transaction.update(zone_ref, {
            "severity":    new_sev,
            "reportCount": new_count,
            "lastUpdated": datetime.utcnow(),
        })
    else:
        transaction.set(zone_ref, {
            "center":      {"lat": lat, "lng": lng},
            "severity":    float(severity),
            "reportCount": 1,
            "lastUpdated": datetime.utcnow(),
        })


def write_processed_report(report_id, lat, lng, severity, category, people_affected, summary):
    try:
        zone_id = f"{math.floor(lat * 100) / 100}_{math.floor(lng * 100) / 100}"

        processed_ref = db.collection("processedReports").document()
        processed_ref.set({
            "reportId":      report_id,
            "zone":          zone_id,
            "severity":      severity,
            "category":      category,
            "peopleAffected": people_affected,
            "summary":       summary,
        })

        zone_ref = db.collection("zones").document(zone_id)
        _update_zone_tx(db.transaction(), zone_ref, lat, lng, severity)

        return processed_ref.id
    except Exception as e:
        print(f"Error writing processed report: {e}")
        raise HTTPException(status_code=500, detail="Failed to write processed report")


# ── Zones ────────────────────────────────────────────────────────────────────
def get_all_zones():
    try:
        zones = []
        for doc in db.collection("zones").stream():
            data = doc.to_dict()
            data["id"] = doc.id
            zones.append(data)
        return zones
    except Exception as e:
        print(f"Error fetching zones: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch zones")


# ── Dispatches ───────────────────────────────────────────────────────────────
def get_recent_dispatches():
    try:
        dispatches = []
        for doc in (db.collection("dispatches")
                      .where("status", "in", ["pending", "approved"])
                      .stream()):
            data = doc.to_dict()
            data["id"] = doc.id
            dispatches.append(data)
        return dispatches
    except Exception as e:
        print(f"Error fetching recent dispatches: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent dispatches")


def get_dispatch_by_id(dispatch_id: str):
    try:
        doc = db.collection("dispatches").document(dispatch_id).get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None
    except Exception as e:
        print(f"Error fetching dispatch {dispatch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dispatch")


def write_dispatch(volunteer_team, zone_id, route_polyline, ai_reason, confidence, status="pending"):
    try:
        ref = db.collection("dispatches").document()
        ref.set({
            "volunteerTeam": volunteer_team,
            "zoneId":        zone_id,
            "routePolyline": route_polyline,
            "aiReason":      ai_reason,
            "confidence":    confidence,
            "status":        status,
            "approvedBy":    None,
        })
        return ref.id
    except Exception as e:
        print(f"Error writing dispatch: {e}")
        raise HTTPException(status_code=500, detail="Failed to write dispatch")


def update_dispatch_route(dispatch_id, new_polyline, rerouted_at, reroute_reason):
    try:
        db.collection("dispatches").document(dispatch_id).update({
            "routePolyline": new_polyline,
            "reroutedAt":    rerouted_at,
            "rerouteReason": reroute_reason,
        })
    except Exception as e:
        print(f"Error updating dispatch route {dispatch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update dispatch route")


# ── Volunteers ───────────────────────────────────────────────────────────────
def get_nearest_available_volunteer(lat: float, lng: float):
    try:
        closest, min_dist = None, float("inf")
        for doc in db.collection("volunteers").where("available", "==", True).stream():
            v = doc.to_dict()
            v["id"] = doc.id
            if v.get("lat") is not None and v.get("lng") is not None:
                d = haversine(lat, lng, v["lat"], v["lng"])
                if d < min_dist:
                    min_dist, closest = d, v
        return closest
    except Exception as e:
        print(f"Error fetching nearest volunteer: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch nearest volunteer")


def get_volunteer_by_team_name(team_name: str):
    """Used by the blocked-road endpoint — keeps Firestore out of route handlers."""
    try:
        for doc in (db.collection("volunteers")
                      .where("teamName", "==", team_name)
                      .limit(1)
                      .stream()):
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error fetching volunteer by team name: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch volunteer")

def approve_dispatch(dispatch_id: str, approved_by: str):
    try:
        db.collection("dispatches").document(dispatch_id).update({
            "status":     "approved",
            "approvedBy": approved_by,
        })
    except Exception as e:
        print(f"Error approving dispatch {dispatch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve dispatch")