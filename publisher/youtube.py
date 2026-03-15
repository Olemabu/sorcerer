"""
SORCERER — YouTube Publisher
===========================
Uploads the master video to YouTube with full metadata.
Uses the YouTube Data API v3 (already configured in SORCERER).

Requires: google-auth google-auth-oauthlib google-api-python-client
  pip install google-auth google-auth-oauthlib google-api-python-client
"""

import os
import json
import time
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def upload(video_path, captions, script, token_file, log_fn=print):
    """
    Upload video to YouTube.

    Args:
        video_path  : path to the master video file
        captions    : captions dict from captions.py (youtube key)
        script      : script dict (for thumbnail direction + tags)
        token_file  : path to OAuth token JSON (see setup below)
        log_fn      : logging function

    Returns:
        (success, video_id_or_error)

    ── OAuth Setup (one-time) ──────────────────────────────────────
    YouTube requires OAuth 2.0 — API key alone is not enough for upload.

    1. Go to console.cloud.google.com
    2. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
    3. Application type: Desktop app
    4. Download the client_secret.json file
    5. Run: python -c "from publisher.youtube import get_token; get_token('client_secret.json', 'yt_token.json')"
    6. A browser opens — log in with your YouTube account
    7. Token saved to yt_token.json — add path to .env as YOUTUBE_TOKEN_FILE
    ────────────────────────────────────────────────────────────────
    """
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        log_fn("  ⚠️  Missing: pip install google-auth google-auth-oauthlib google-api-python-client")
        return False, "missing google client libraries"

    if not Path(token_file).exists():
        log_fn(f"  ⚠️  YouTube OAuth token not found: {token_file}")
        log_fn("      Run: python -c \"from publisher.youtube import get_token; get_token('client_secret.json', 'yt_token.json')\"")
        return False, "no oauth token"

    try:
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            Path(token_file).write_text(creds.to_json())

        youtube = build("youtube", "v3", credentials=creds)

        yt_caps = captions.get("youtube", {})
        tags    = yt_caps.get("tags", [])
        if script:
            tags = list(set(tags + script.get("seo_tags", [])))

        body = {
            "snippet": {
                "title":       yt_caps.get("title", "Untitled"),
                "description": yt_caps.get("description", ""),
                "tags":        tags[:30],   # YT max 30 tags
                "categoryId":  "28",        # Science & Technology
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True,
                                mimetype="video/mp4")

        log_fn("  📤  Uploading to YouTube...")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                log_fn(f"  📤  YouTube upload: {pct}%")

        video_id = response.get("id", "")
        url      = f"https://youtube.com/watch?v={video_id}"
        log_fn(f"  ✅  YouTube → {url}")
        return True, video_id

    except Exception as e:
        log_fn(f"  ❌  YouTube upload failed: {e}")
        return False, str(e)


def get_token(client_secret_file, token_output_file):
    """Run this once to generate the OAuth token."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow  = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
    creds = flow.run_local_server(port=0)
    Path(token_output_file).write_text(creds.to_json())
    print(f"✅ Token saved to {token_output_file}")
    print(f"   Add to .env: YOUTUBE_TOKEN_FILE={token_output_file}")
