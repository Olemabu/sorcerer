"""
SORCERER — Facebook Publisher
============================
Posts to Facebook Page:
  - Feed video  : full 16:9 master video
  - Reels       : vertical 9:16 clip (max 90 sec)

Requires:
  - Facebook Page (not personal profile)
  - Meta Developer App with pages_manage_posts + pages_read_engagement
  - Long-lived Page Access Token (valid 60 days, auto-refreshed)

Setup:
  1. Go to developers.facebook.com → Create App → Business
  2. Add "Facebook Login" product
  3. Get a short-lived token from Graph API Explorer
  4. Exchange for long-lived token (see get_long_lived_token below)
  5. Add to .env: FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN
"""

import requests
import time
from pathlib import Path

GRAPH = "https://graph.facebook.com/v19.0"


def _page_headers(token):
    return {"Authorization": f"Bearer {token}"}


def upload_feed_video(video_path, captions, page_id, page_token, log_fn=print):
    """
    Upload full video to Facebook Page feed.
    Returns (success, post_id_or_error)
    """
    fb  = captions.get("facebook_feed", {})
    cap = fb.get("caption", "")
    tags = " ".join(fb.get("hashtags", []))
    description = f"{cap}\n\n{tags}".strip()

    try:
        log_fn("  📤  Uploading to Facebook feed...")

        # Step 1: start upload session
        r = requests.post(
            f"{GRAPH}/{page_id}/videos",
            params={"access_token": page_token},
            data={
                "upload_phase": "start",
                "file_size":    Path(video_path).stat().st_size,
            },
            timeout=30,
        )
        r.raise_for_status()
        session = r.json()
        upload_session_id = session["upload_session_id"]
        video_id          = session["video_id"]

        # Step 2: upload file
        with open(video_path, "rb") as f:
            chunk = f.read()

        r2 = requests.post(
            f"{GRAPH}/{page_id}/videos",
            params={"access_token": page_token},
            data={
                "upload_phase":     "transfer",
                "upload_session_id": upload_session_id,
                "start_offset":     0,
            },
            files={"video_file_chunk": ("video.mp4", chunk, "video/mp4")},
            timeout=300,
        )
        r2.raise_for_status()

        # Step 3: finish
        r3 = requests.post(
            f"{GRAPH}/{page_id}/videos",
            params={"access_token": page_token},
            data={
                "upload_phase":     "finish",
                "upload_session_id": upload_session_id,
                "description":       description,
                "published":         True,
            },
            timeout=30,
        )
        r3.raise_for_status()
        post_id = r3.json().get("id", video_id)
        log_fn(f"  ✅  Facebook feed → post ID: {post_id}")
        return True, post_id

    except Exception as e:
        log_fn(f"  ❌  Facebook feed failed: {e}")
        return False, str(e)


def upload_reel(clip_path, captions, page_id, page_token, log_fn=print):
    """
    Upload vertical clip as Facebook Reel.
    clip_path must be the 9:16 vertical clip.
    """
    fb  = captions.get("facebook_reels", {})
    cap = fb.get("caption", "")
    tags = " ".join(fb.get("hashtags", []))
    description = f"{cap} {tags}".strip()

    try:
        log_fn("  📤  Uploading Facebook Reel...")

        # Reels upload endpoint
        r = requests.post(
            f"{GRAPH}/{page_id}/video_reels",
            params={"access_token": page_token},
            data={"upload_phase": "start"},
            timeout=30,
        )
        r.raise_for_status()
        data       = r.json()
        video_id   = data["video_id"]
        upload_url = data["upload_url"]

        # Upload to the provided URL
        file_size = Path(clip_path).stat().st_size
        with open(clip_path, "rb") as f:
            r2 = requests.post(
                upload_url,
                headers={
                    "Authorization":       f"OAuth {page_token}",
                    "offset":              "0",
                    "file_size":           str(file_size),
                    "Content-Type":        "application/octet-stream",
                },
                data=f,
                timeout=300,
            )
        r2.raise_for_status()

        # Publish
        r3 = requests.post(
            f"{GRAPH}/{page_id}/video_reels",
            params={"access_token": page_token},
            data={
                "video_id":      video_id,
                "upload_phase":  "finish",
                "video_state":   "PUBLISHED",
                "description":   description,
            },
            timeout=30,
        )
        r3.raise_for_status()
        log_fn(f"  ✅  Facebook Reel → video ID: {video_id}")
        return True, video_id

    except Exception as e:
        log_fn(f"  ❌  Facebook Reel failed: {e}")
        return False, str(e)


def get_long_lived_token(app_id, app_secret, short_token):
    """
    Exchange short-lived token for long-lived (60-day) Page token.
    Run this once, save the result to .env as FACEBOOK_PAGE_TOKEN.
    """
    r = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "grant_type":        "fb_exchange_token",
            "client_id":         app_id,
            "client_secret":     app_secret,
            "fb_exchange_token": short_token,
        },
    )
    r.raise_for_status()
    long_token = r.json()["access_token"]

    # Get page token from long-lived user token
    r2 = requests.get(
        f"{GRAPH}/me/accounts",
        params={"access_token": long_token},
    )
    r2.raise_for_status()
    pages = r2.json().get("data", [])
    for page in pages:
        print(f"Page: {page['name']} | ID: {page['id']} | Token: {page['access_token'][:30]}...")

    print("\nAdd to .env:")
    print("FACEBOOK_PAGE_ID=<page id from above>")
    print("FACEBOOK_PAGE_TOKEN=<page access_token from above>")
    return pages
