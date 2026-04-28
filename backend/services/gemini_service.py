import json
from fastapi import HTTPException
from google.genai import types
from config import gemini_client, GEMINI_MODEL_FLASH   # shared client from config.py

CLASSIFIER_PROMPT = (
    "You are a disaster relief classifier. Given this field report, extract: "
    "severity (1–10 integer), category (exactly one of: medical, food, shelter, evacuation), "
    "estimated people affected (integer), 1-sentence summary. "
    "Respond ONLY in raw JSON with keys: severity, category, peopleAffected, summary. "
    "No markdown, no explanation."
)

VALID_CATEGORIES = {"medical", "food", "shelter", "evacuation"}


def classify_report(text: str) -> dict:
    """Call Gemini Flash to classify a raw field report. Retries once on parse failure."""
    last_error = None
    for attempt in range(2):
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL_FLASH,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=CLASSIFIER_PROMPT,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text.strip()

            # Strip markdown fences if the model ignores the mime-type hint
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            data = json.loads(raw)

            required = {"severity", "category", "peopleAffected", "summary"}
            if not required.issubset(data.keys()):
                raise ValueError(f"Missing keys: {required - data.keys()}")

            data["severity"]       = int(data["severity"])
            data["peopleAffected"] = int(data["peopleAffected"])
            data["category"]       = str(data["category"]).lower().strip()
            data["summary"]        = str(data["summary"])

            if data["category"] not in VALID_CATEGORIES:
                raise ValueError(f"Invalid category '{data['category']}'")

            if not (1 <= data["severity"] <= 10):
                data["severity"] = max(1, min(10, data["severity"]))

            return data

        except Exception as e:
            last_error = e
            print(f"Gemini classify attempt {attempt + 1} failed: {e}")

    raise HTTPException(
        status_code=422,
        detail=f"Gemini classification failed after 2 attempts: {last_error}",
    )