import os
import firebase_admin
from google import genai
from dotenv import load_dotenv
from firebase_admin import credentials, firestore, storage

load_dotenv()

# ── Environment variables ───────────────────────────────────────────────────
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_MAPS_API_KEY             = os.getenv("GOOGLE_MAPS_API_KEY")
GOOGLE_CLOUD_PROJECT            = os.getenv("GOOGLE_CLOUD_PROJECT")
GEMINI_MODEL_FLASH              = os.getenv("GEMINI_MODEL_FLASH", "gemini-2.5-flash")
GEMINI_MODEL_PRO                = os.getenv("GEMINI_MODEL_PRO",   "gemini-2.5-pro")
VERTEX_LOCATION                 = os.getenv("VERTEX_LOCATION",    "us-central1")

# ── Gemini via Vertex AI (billed to GCP — no AI Studio key needed) ──────────
if not GOOGLE_CLOUD_PROJECT:
    raise EnvironmentError(
        "GOOGLE_CLOUD_PROJECT is not set. Add it to your .env file or Cloud Run env vars."
    )
# Uses Application Default Credentials (ADC):
#   • Locally: run `gcloud auth application-default login`
#   • Cloud Run: automatically uses the attached service account
gemini_client = genai.Client(
    vertexai=True,
    project=GOOGLE_CLOUD_PROJECT,
    location=VERTEX_LOCATION,
)

# ── Firebase Admin ──────────────────────────────────────────────────────────
def init_firebase():
    if firebase_admin._apps:
        return  # already initialised

    options = {}
    if GOOGLE_CLOUD_PROJECT:
        options["projectId"]     = GOOGLE_CLOUD_PROJECT
        options["storageBucket"] = f"crisisgrid-494418.firebasestorage.app"

    if GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        # Local dev: explicit service-account JSON
        cred = credentials.Certificate(GOOGLE_APPLICATION_CREDENTIALS)
        firebase_admin.initialize_app(cred, options)
    else:
        # Cloud Run: use the attached service account (ADC) — no JSON file needed
        firebase_admin.initialize_app(options=options)

init_firebase()

# ── Singletons (import these everywhere, never re-initialise) ───────────────
db     = firestore.client()
bucket = storage.bucket()