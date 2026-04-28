from datetime import timedelta
from config import bucket


def generate_signed_url(blob_name: str) -> str | None:
    try:
        blob = bucket.blob(blob_name)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="GET",
        )
    except Exception as e:
        print(f"Error generating signed URL for '{blob_name}': {e}")
        return None


def resolve_photo_url(photo_url: str) -> str | None:
    if not photo_url:
        return None
    if photo_url.startswith("http"):
        return photo_url
    if photo_url.startswith("gs://"):
        parts = photo_url.split("/")
        if len(parts) > 3:
            blob_name = "/".join(parts[3:])
            return generate_signed_url(blob_name)
    return generate_signed_url(photo_url)
