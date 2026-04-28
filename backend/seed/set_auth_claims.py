"""
Run once after creating the three test accounts in Firebase Console:
    python seed/set_auth_claims.py

Sets custom role claims on the three hardcoded test accounts so Member 1's
Flutter app and dashboard can enforce role-based access.

HOW TO GET UIDs:
  1. Go to https://console.firebase.google.com
  2. Select your project → Authentication → Users
  3. Find each user and copy the UID from the User UID column and paste below.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from firebase_admin import auth
from config import db  # ensures Firebase is initialised

# ── Paste your UIDs here ─────────────────────────────────────────────────────
FIELD_WORKER_UID  = "WqgZLsWW2mbZHdycV7TNupHgvY92"
COORDINATOR_UID   = "5YZaVOB7f0OEjU6yrlXGSxdFxJi1"
ADMIN_UID         = "hiuN8XPJD8U6riiyMY8PZdhbEHm2"
# ────────────────────────────────────────────────────────────────────────────


def set_claims():
    if "PASTE" in FIELD_WORKER_UID or "PASTE" in COORDINATOR_UID or "PASTE" in ADMIN_UID:
        print("ERROR: Replace the placeholder UIDs in this script before running.")
        sys.exit(1)

    auth.set_custom_user_claims(FIELD_WORKER_UID, {"role": "field_worker"})
    print(f"✓ field_worker@test.com ({FIELD_WORKER_UID}) → role: field_worker")

    auth.set_custom_user_claims(COORDINATOR_UID, {"role": "coordinator"})
    print(f"✓ coordinator@test.com  ({COORDINATOR_UID}) → role: coordinator")

    auth.set_custom_user_claims(ADMIN_UID, {"role": "admin"})
    print(f"✓ admin@test.com        ({ADMIN_UID}) → role: admin")

    print("\nDone. Tell Member 1 to sign out and back in for claims to take effect.")


if __name__ == "__main__":
    set_claims()