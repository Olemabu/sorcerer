"""
SORCERER — TikTok Publisher
==========================
Uploads vertical clips to TikTok via Content Posting API.

Format requirements:
  - Ratio    : 9:16 vertical (handled by clipper.py)
  - Max size : 4GB
  - Max length: 10 minutes
  - Codec    : H.264

Setup (takes 1-2 weeks for API approval):
  1. Go to developers.tiktok.com → Create App
  2. Add "Content Posting API" product
  3. Submit for review (state: personal content automation)
  4. Once approved, generate access token
  5. Add to .env: TIKTOK_ACCESS_TOKEN and TIKTOK_OPEN_ID

Note: TikTok API requires HTTPS callback URLs during OAuth.
      For personal use, use the direct token from developer dashboard.
"""

import requests
import json
import time
from pathlib import Path

TIKTOK_API = "https://open.tiktokapis.com/v2"


def upload(clip_path, captions, access_token, open_id, log_fn=print):
    """
    Upload vertical clip to TikTok.

    Args:
        clip_path    : path to 9:16 vertical clip
        captions     : captions dict (tiktok key)
        access_token : TikTok OAuth access token
        open_id      : TikTok user open_id
        log_fn       : logging function

    Returns:
        (success, post_id_or_error)
    """
    tk     = captions.get("tiktok", {})
    cap    = tk.get("caption", "")
    tags   = " ".join(tk.get("hashtags", []))
    text   = f"{cap} {tags}".strip()[:2200]  # TikTok cap limit

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json; charset=UTF-8",
    }

    try:
        log_fn("  📤  Initiating TikTok upload...")

        file_size = Path(clip_path).stat().st_size

        # Step 1: Init upload
        r = requests.post(
            f"{TIKTOK_API}/post/publish/video/init/",
            headers=headers,
            json={
                "post_info": {
                    "title":              text,
                    "privacy_level":      "PUBLIC_TO_EVERYONE",
                    "disable_duet":       False,
                    "disable_comment":    False,
                    "disable_stitch":     False,
                    "video_cover_timestamp_ms": 2000,
                },
                "source_info": {
                    "source":          "FILE_UPLOAD",
                    "video_size":      file_size,
                    "chunk_size":      file_size,
                    "total_chunk_count": 1,
                },
            },
            timeout=30,
        )
        r.raise_for_status()
        data       = r.json().get("data", {})
        publish_id = data.get("publish_id", "")
        upload_url = data.get("upload_url", "")

        if not upload_url:
            return False, f"No upload URL returned: {r.text[:200]}"

        # Step 2: Upload file
        log_fn("  📤  Uploading TikTok video...")
        with open(clip_path, "rb") as f:
            video_data = f.read()

        r2 = requests.put(
            upload_url,
            headers={
                "Content-Range":  f"bytes 0-{file_size - 1}/{file_size}",
                "Content-Type":   "video/mp4",
                "Content-Length": str(file_size),
            },
            data=video_data,
            timeout=300,
        )
        r2.raise_for_status()

        # Step 3: Poll for status
        log_fn("  ⏳  Waiting for TikTok processing...")
        for attempt in range(12):
            time.sleep(5)
            r3 = requests.post(
                f"{TIKTOK_API}/post/publish/status/fetch/",
                headers=headers,
                json={"publish_id": publish_id},
                timeout=15,
            )
            status = r3.json().get("data", {}).get("status", "")
            if status == "PUBLISH_COMPLETE":
                log_fn(f"  ✅  TikTok published → publish_id: {publish_id}")
                return True, publish_id
            elif status in ("FAILED", "PUBLISH_FAILED"):
                return False, f"TikTok publish failed: {r3.json()}"

        log_fn("  ⚠️  TikTok processing timeout — video may still be publishing")
        return True, publish_id

    except Exception as e:
        log_fn(f"  ❌  TikTok upload failed: {e}")
        return False, str(e)
