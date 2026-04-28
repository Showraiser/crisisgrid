"""
Run once before starting development:
    python seed/seed_volunteers.py

Seeds 8 volunteer teams across Assam into the `volunteers` Firestore collection.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import db  # initialises Firebase

VOLUNTEERS = [
    {"teamName": "Team Alpha",   "lat": 26.1445, "lng": 91.7362, "specialization": "medical",  "available": True},
    {"teamName": "Team Bravo",   "lat": 26.1434, "lng": 91.7898, "specialization": "rescue",   "available": True},
    {"teamName": "Team Charlie", "lat": 26.7465, "lng": 94.2026, "specialization": "food",     "available": True},
    {"teamName": "Team Delta",   "lat": 24.8333, "lng": 92.7789, "specialization": "shelter",  "available": True},
    {"teamName": "Team Echo",    "lat": 27.4728, "lng": 94.9120, "specialization": "medical",  "available": True},
    {"teamName": "Team Foxtrot", "lat": 26.6338, "lng": 92.7926, "specialization": "rescue",   "available": True},
    {"teamName": "Team Golf",    "lat": 26.3466, "lng": 92.6840, "specialization": "food",     "available": True},
    {"teamName": "Team Hotel",   "lat": 26.3226, "lng": 91.0088, "specialization": "shelter",  "available": True},
]


def seed():
    batch = db.batch()
    col   = db.collection("volunteers")
    for v in VOLUNTEERS:
        ref = col.document()
        batch.set(ref, v)
    batch.commit()
    print(f"✓ Seeded {len(VOLUNTEERS)} volunteer teams into Firestore.")


if __name__ == "__main__":
    seed()
