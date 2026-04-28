from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.manager_agent import ManagerAgent

router  = APIRouter()
manager = ManagerAgent()


class ReportPayload(BaseModel):
    reportId: str


@router.post("/trigger/new-report")
def new_report_trigger(payload: ReportPayload):
    """
    Called whenever a new report document is written to Firestore.
    Member 1's Flutter app (or a Firestore trigger) hits this endpoint.
    """
    try:
        results       = manager.run({"trigger": "new_report"})
        ingestion     = results.get("ingestion", {})
        processed_ids = ingestion.get("processed_ids", [])
        return {"status": "success", "processedReportIds": processed_ids}
    except Exception as e:
        print(f"Error in /trigger/new-report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
