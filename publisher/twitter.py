"""
SORCERER — Twitter/X Publisher
==============================
Posts a 3-tweet thread with landscape clip.

API tier requirements:
  Free  ($0)    : Read only — cannot post
  Basic ($100/mo): Text + images only — no video upload
  Pro   ($5k/mo) : Full video upload

Strategy for Basic tier ($100/mo):
  Post a 3-tweet thread with:
    Tweet 1: Hook text + YouTube thumbnail image
    Tweet 2: Tension builder + key stat
    Tweet 3: Full YouTube link + question CTA

  This is the smart play — Twitter/X drives YouTube clicks
  better than native video anyway. The algorithm deprioritises
  external links in single tweets, but threads with engagement
  break through.

For Pro tier: native video upload is also implemented below.

Setup:
  1. Apply at developer.twitter.com (takes 1-3 days)
  2. Create a Project → App → Keys & Tokens
  3. Generate: API Key, API Secret, Access Token, Access Token Secret
  4. Add all 4 to .env
"""

import requests
import json
import base64
import time
from pathlib import Path
from requests_oauthlib import OAuth1


def _auth(api_key, api_secret, access_token, access_secret):
    return OAuth1(api_key, api_secret, access_token, access_secret)


def post_thread(captions, thumbnail_path, youtube_url,
                api_key, api_secret, access_token, access_secret,
                log_fn=print):
    """
    Post a 3-tweet thread (Basic tier — no video required).
    Attaches thumbnail image to tweet 1.

    Returns (success, first_tweet_id_or_error)
    """
    try:
        from requests_oauthlib import OAuth1
    except ImportError:
        log_fn("  ⚠️  Missing: pip install requests-oauthlib")
        return False, "missing requests-oauthlib"

    auth = _auth(api_key, api_secret, access_token, access_secret)
    tw   = captions.get("twitter", {})

    tweet1_text = tw.get("tweet_1", "")
    tweet2_text = tw.get("tweet_2", "")
    tweet3_text = tw.get("tweet_3", "").replace("[LINK]", youtube_url)

    try:
        media_id = None

        # Upload thumbnail if available
        if thumbnail_path and Path(thumbnail_path).exists():
            log_fn("  🖼️  Uploading thumbnail to Twitter...")
            with open(thumbnail_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")

            r_media = requests.post(
                "https://upload.twitter.com/1.1/media/upload.json",
                auth=auth,
                data={"media_data": img_data},
                timeout=30,
            )
            if r_media.ok:
                media_id = r_media.json().get("media_id_string")

        log_fn("  📤  Posting Twitter thread...")

        # Tweet 1
        body1 = {"text": tweet1_text}
        if media_id:
            body1["media"] = {"media_ids": [media_id]}

        r1 = requests.post(
            "https://api.twitter.com/2/tweets",
            auth=auth,
            json=body1,
            timeout=15,
        )
        r1.raise_for_status()
        t1_id = r1.json()["data"]["id"]
        time.sleep(1)

        # Tweet 2 (reply to tweet 1)
        r2 = requests.post(
            "https://api.twitter.com/2/tweets",
            auth=auth,
            json={"text": tweet2_text, "reply": {"in_reply_to_tweet_id": t1_id}},
            timeout=15,
        )
        r2.raise_for_status()
        t2_id = r2.json()["data"]["id"]
        time.sleep(1)

        # Tweet 3 (reply to tweet 2)
        r3 = requests.post(
            "https://api.twitter.com/2/tweets",
            auth=auth,
            json={"text": tweet3_text, "reply": {"in_reply_to_tweet_id": t2_id}},
            timeout=15,
        )
        r3.raise_for_status()
        t3_id = r3.json()["data"]["id"]

        url = f"https://twitter.com/i/web/status/{t1_id}"
        log_fn(f"  ✅  Twitter thread posted → {url}")
        return True, t1_id

    except Exception as e:
        log_fn(f"  ❌  Twitter post failed: {e}")
        return False, str(e)


def post_video_tweet(clip_path, captions, youtube_url,
                     api_key, api_secret, access_token, access_secret,
                     log_fn=print):
    """
    Upload landscape clip as native video tweet (Pro tier — $5k/mo).
    Falls back to thread if upload fails.
    """
    auth = _auth(api_key, api_secret, access_token, access_secret)
    tw   = captions.get("twitter", {})

    try:
        log_fn("  📤  Uploading video to Twitter (Pro tier)...")
        file_size = Path(clip_path).stat().st_size

        # Init
        r_init = requests.post(
            "https://upload.twitter.com/1.1/media/upload.json",
            auth=auth,
            data={
                "command":      "INIT",
                "total_bytes":  file_size,
                "media_type":   "video/mp4",
                "media_category": "tweet_video",
            },
            timeout=30,
        )
        r_init.raise_for_status()
        media_id = r_init.json()["media_id_string"]

        # Append in 5MB chunks
        chunk_size = 5 * 1024 * 1024
        with open(clip_path, "rb") as f:
            segment = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                requests.post(
                    "https://upload.twitter.com/1.1/media/upload.json",
                    auth=auth,
                    data={"command": "APPEND", "media_id": media_id, "segment_index": segment},
                    files={"media": chunk},
                    timeout=120,
                ).raise_for_status()
                segment += 1

        # Finalize
        requests.post(
            "https://upload.twitter.com/1.1/media/upload.json",
            auth=auth,
            data={"command": "FINALIZE", "media_id": media_id},
            timeout=30,
        ).raise_for_status()

        # Wait for processing
        for _ in range(20):
            time.sleep(3)
            r_status = requests.get(
                "https://upload.twitter.com/1.1/media/upload.json",
                auth=auth,
                params={"command": "STATUS", "media_id": media_id},
                timeout=15,
            )
            state = r_status.json().get("processing_info", {}).get("state", "")
            if state == "succeeded":
                break
            elif state == "failed":
                return False, "Video processing failed"

        # Post tweet
        text = f"{tw.get('tweet_1','')} {youtube_url}"[:280]
        r_tweet = requests.post(
            "https://api.twitter.com/2/tweets",
            auth=auth,
            json={"text": text, "media": {"media_ids": [media_id]}},
            timeout=15,
        )
        r_tweet.raise_for_status()
        tweet_id = r_tweet.json()["data"]["id"]
        log_fn(f"  ✅  Twitter video posted → tweet ID: {tweet_id}")
        return True, tweet_id

    except Exception as e:
        log_fn(f"  ⚠️  Twitter video upload failed ({e}) — falling back to thread")
        return post_thread(captions, None, youtube_url,
                           api_key, api_secret, access_token, access_secret, log_fn)
