"""
Ingestion Agent — ADK LlmAgent that classifies raw field reports with Gemini Flash
and writes structured output to Firestore.
"""
from google.adk.agents import LlmAgent
from config import GEMINI_MODEL_FLASH
from services.firestore_service import get_unprocessed_reports, write_processed_report
from services.gemini_service import classify_report


# ── Tool functions (plain Python — ADK discovers these via the tools= list) ──

def fetch_unprocessed_reports() -> dict:
    """Fetch all reports that have not yet been processed by Gemini."""
    reports = get_unprocessed_reports()
    return {"reports": reports, "count": len(reports)}


def classify_and_store_report(report_id: str, text: str, lat: float, lng: float) -> dict:
    """
    Classify a single report with Gemini Flash and write the result to
    processedReports + update the zone severity average.
    """
    classification = classify_report(text)
    processed_id   = write_processed_report(
        report_id      = report_id,
        lat            = lat,
        lng            = lng,
        severity       = classification["severity"],
        category       = classification["category"],
        people_affected = classification["peopleAffected"],
        summary        = classification["summary"],
    )
    return {"processedId": processed_id, "classification": classification}


# ── ADK Agent definition ────────────────────────────────────────────────────
ingestion_agent = LlmAgent(
    name        = "ingestion_agent",
    model       = GEMINI_MODEL_FLASH,
    description = "Fetches unprocessed disaster reports and classifies them using Gemini Flash.",
    instruction = (
        "You are the Ingestion Agent for CrisisGrid. "
        "First call fetch_unprocessed_reports. "
        "Then for each report returned, call classify_and_store_report with its id, text, lat, and lng. "
        "Return the list of all processedIds created."
    ),
    tools = [fetch_unprocessed_reports, classify_and_store_report],
)


# ── Convenience wrapper (used by ManagerAgent) ──────────────────────────────
class IngestionAgent:
    """Thin wrapper so ManagerAgent can call .run() synchronously."""

    def run(self, context: dict) -> dict:
        print("Ingestion Agent: processing unprocessed reports...")
        reports = get_unprocessed_reports()
        if not reports:
            print("Ingestion Agent: nothing to process.")
            return {"processed_ids": []}

        processed_ids = []
        for report in reports:
            try:
                classification = classify_report(report.get("text", ""))
                pid = write_processed_report(
                    report_id       = report["id"],
                    lat             = report.get("lat", 0.0),
                    lng             = report.get("lng", 0.0),
                    severity        = classification["severity"],
                    category        = classification["category"],
                    people_affected = classification["peopleAffected"],
                    summary         = classification["summary"],
                )
                processed_ids.append(pid)
                print(f"  ✓ {report['id']} → {pid}")
            except Exception as e:
                print(f"  ✗ {report['id']}: {e}")

        return {"processed_ids": processed_ids}
