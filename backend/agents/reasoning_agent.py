"""
Reasoning Agent — ADK LlmAgent using Gemini Pro for heavy multi-zone analysis.
Also queries Open-Meteo for live precipitation data (MCP wildcard).
"""
import json
import requests
from datetime import datetime

from google.genai import types
from google.adk.agents import LlmAgent

from config import GEMINI_MODEL_PRO, GEMINI_MODEL_FLASH, gemini_client
from services.firestore_service import get_all_zones, get_recent_dispatches

def _json_default(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)

_REASONING_INSTRUCTION = (
    "You are a strategic disaster response coordinator for CrisisGrid. "
    "You receive zone clusters grouped by severity tier (high 7-10, medium 4-6, low 1-3) "
    "and a list of zone IDs that already have a pending or approved dispatch. "
    "Select the SINGLE highest-priority zone that needs a new dispatch. "
    "Never select a zone that is already dispatched. "
    "Respond ONLY in raw JSON with keys: "
    "targetZoneId (string), severity (float), reason (string), confidence (float 0.0-1.0). "
    "No markdown."
)


# ── Tool functions ───────────────────────────────────────────────────────────

def fetch_zone_clusters() -> dict:
    """Group all active zones by severity tier for the reasoning model."""
    zones = get_all_zones()
    clusters = {"high": [], "medium": [], "low": []}
    for z in zones:
        sev = z.get("severity", 0)
        if sev >= 7:
            clusters["high"].append(z)
        elif sev >= 4:
            clusters["medium"].append(z)
        else:
            clusters["low"].append(z)
    return {"clusters": clusters, "total_zones": len(zones)}


def fetch_dispatched_zone_ids() -> dict:
    """Return zone IDs that already have an active (pending/approved) dispatch."""
    dispatches = get_recent_dispatches()
    zone_ids = list({d.get("zoneId") for d in dispatches if d.get("zoneId")})
    return {"dispatched_zone_ids": zone_ids}


def check_weather_urgency(lat: float, lng: float) -> dict:
    """
    Query Open-Meteo for precipitation in the next 6 hours.
    Returns whether heavy rain (>5 mm total) is forecast.
    This is the MCP external-data integration.
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lng}&hourly=precipitation&forecast_days=1"
        )
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            hourly = resp.json().get("hourly", {}).get("precipitation", [])
            hour   = datetime.utcnow().hour
            total  = sum(hourly[hour : hour + 6]) if len(hourly) >= hour + 6 else 0
            heavy  = total > 5.0
            return {"heavy_rain_forecast": heavy, "total_mm_next_6h": round(total, 2)}
    except Exception as e:
        print(f"Open-Meteo error: {e}")
    return {"heavy_rain_forecast": False, "total_mm_next_6h": 0}


# ── ADK Agent definition ─────────────────────────────────────────────────────
reasoning_agent = LlmAgent(
    name        = "reasoning_agent",
    model       = GEMINI_MODEL_PRO,
    description = "Analyses zone severity clusters to identify the highest-priority dispatch target.",
    instruction = _REASONING_INSTRUCTION,
    tools       = [fetch_zone_clusters, fetch_dispatched_zone_ids, check_weather_urgency],
)


# ── Convenience wrapper ───────────────────────────────────────────────────────
class ReasoningAgent:
    """Synchronous wrapper for use by ManagerAgent."""

    def run(self, context: dict) -> dict | None:
        print("Reasoning Agent: analysing zones...")

        zones = get_all_zones()
        if not zones:
            print("Reasoning Agent: no zones found.")
            return None

        clusters = {"high": [], "medium": [], "low": []}
        for z in zones:
            sev = z.get("severity", 0)
            if sev >= 7:
                clusters["high"].append(z)
            elif sev >= 4:
                clusters["medium"].append(z)
            else:
                clusters["low"].append(z)

        dispatched_ids = [d.get("zoneId") for d in get_recent_dispatches()]

        prompt = json.dumps({"clusters": clusters, "dispatched_zones": dispatched_ids}, default=_json_default)

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL_PRO,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_REASONING_INSTRUCTION,
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            result = json.loads(raw)
        except Exception as e:
            print(f"Reasoning Agent: JSON parse error: {e}")
            return None

        target_id = result.get("targetZoneId")
        if not target_id:
            return None

        # Live weather check (Open-Meteo — external MCP integration)
        selected = next((z for z in zones if z["id"] == target_id), None)
        if selected and "center" in selected:
            weather = check_weather_urgency(selected["center"]["lat"], selected["center"]["lng"])
            if weather["heavy_rain_forecast"]:
                result["reason"] = (
                    result.get("reason", "") +
                    f" | Weather alert: {weather['total_mm_next_6h']} mm rain forecast in next 6h — urgency elevated."
                )
                result["confidence"] = min(1.0, result.get("confidence", 0.8) + 0.1)

        print(f"Reasoning Agent: target zone = {target_id}, confidence = {result.get('confidence')}")
        return result