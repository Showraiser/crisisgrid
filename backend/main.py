from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from triggers.report_trigger      import router as trigger_router
from scheduler.dispatch_scheduler import router as scheduler_router
from endpoints.dispatch_routes    import router as dispatch_router

app = FastAPI(
    title       = "CrisisGrid Backend",
    description = "Real-time disaster coordination API — Member 2",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

app.include_router(trigger_router)
app.include_router(scheduler_router)
app.include_router(dispatch_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "crisisgrid-backend"}
