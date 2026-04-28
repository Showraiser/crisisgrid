from fastapi import APIRouter, HTTPException
from agents.manager_agent import ManagerAgent

router  = APIRouter()
manager = ManagerAgent()


def _run_dispatch() -> dict:
    results  = manager.run({"trigger": "scheduled_dispatch"})
    dispatch = results.get("dispatch")
    if dispatch and dispatch.get("dispatch_id"):
        return {"status": "dispatched", "dispatchId": dispatch["dispatch_id"]}
    return {"status": "no_dispatch_needed"}


@router.post("/scheduler/run-dispatch")
def run_dispatch_scheduled():
    """Triggered by Cloud Scheduler every 3 minutes."""
    try:
        return _run_dispatch()
    except Exception as e:
        print(f"Error in scheduled dispatch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/run-dispatch-now")
def run_dispatch_now():
    """Manual trigger — call this during the demo to fire a dispatch immediately."""
    try:
        return _run_dispatch()
    except Exception as e:
        print(f"Error in manual dispatch: {e}")
        raise HTTPException(status_code=500, detail=str(e))
