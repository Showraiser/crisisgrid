# CrisisGrid — Backend

Python (FastAPI) backend for the CrisisGrid disaster coordination platform.
Deployed on Google Cloud Run. Owned by **Member 2**.

---

## Prerequisites

- Python 3.11+
- `gcloud` CLI authenticated (`gcloud auth login`)
- A Firebase project with Firestore enabled
- API keys for Gemini and Google Maps (see **Getting Your API Keys** below)

---

## Local Setup

```bash
cd backend
cp .env.example .env          # fill in all values
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

Health check: `curl http://localhost:8080/health`

---

## Seed Scripts (run in this order)

```bash
# 1. Seed volunteer teams into Firestore
python seed/seed_volunteers.py

# 2. Set auth roles on test accounts
#    First paste the UIDs into seed/set_auth_claims.py
python seed/set_auth_claims.py
```

---

## Running the Demo Simulation

```bash
python simulation/flood_simulation.py
```

Streams 30 flood reports across Assam into Firestore over 90 seconds.
No server needed — run this standalone in a terminal during the demo recording.

---

## Deploy to Cloud Run

```bash
# From repo root
gcloud builds submit --config=backend/cloudbuild.yaml .
```

This builds the Docker image, pushes it to GCR, deploys to Cloud Run (asia-south1),
and creates/updates the Cloud Scheduler job that fires every 3 minutes.

**First deploy only** — add secrets to Secret Manager first:
```bash
echo -n "your-gemini-key"       | gcloud secrets create GEMINI_API_KEY       --data-file=-
echo -n "your-maps-key"         | gcloud secrets create GOOGLE_MAPS_API_KEY  --data-file=-
echo -n "your-gcp-project-id"   | gcloud secrets create GOOGLE_CLOUD_PROJECT --data-file=-
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/health` | Health check |
| POST | `/trigger/new-report` | Process a newly submitted field report |
| POST | `/scheduler/run-dispatch` | Scheduled dispatch (Cloud Scheduler) |
| POST | `/scheduler/run-dispatch-now` | Manual dispatch trigger (use during demo) |
| POST | `/dispatch/{dispatchId}/blocked` | Reroute around a blocked road |

### Example curl commands

```bash
# Manual dispatch (use during demo)
curl -X POST https://YOUR_CLOUD_RUN_URL/scheduler/run-dispatch-now

# Trigger report processing
curl -X POST https://YOUR_CLOUD_RUN_URL/trigger/new-report \
  -H "Content-Type: application/json" \
  -d '{"reportId": "FIRESTORE_DOC_ID"}'

# Report a blocked road
curl -X POST https://YOUR_CLOUD_RUN_URL/dispatch/DISPATCH_ID/blocked \
  -H "Content-Type: application/json" \
  -d '{"blockedLat": 26.58, "blockedLng": 93.17}'
```

---

## Firestore Schema

**`reports`** — written by Flutter app, read by backend
```
{ id, lat, lng, text, photoUrl, timestamp, userId }
```

**`processedReports`** — written by backend, read by dashboard
```
{ id, reportId, zone, severity, category, peopleAffected, summary }
```

**`dispatches`** — written by backend, read by dashboard
```
{ id, volunteerTeam, zoneId, routePolyline, aiReason, confidence, status, approvedBy }
```

**`zones`** — written by backend, read by dashboard (heatmap)
```
{ id, center: {lat, lng}, severity, reportCount, lastUpdated }
```

**`volunteers`** — seeded by backend, read by dispatch agent
```
{ id, teamName, lat, lng, available, specialization }
```
