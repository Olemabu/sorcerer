"""
SORCERER — Soundtrack
======================
Retrieves a mood-matched cinematic soundtrack using Freesound API.

For documentary style: orchestral tension, dark ambient,
occasional ironic contrast moments (upbeat music under
apocalyptic narration = comedy gold).

Setup:
  1. Go to freesound.org/apiv2/ Apply for an API Key
  2. Add to .env: FREESOUND_API_KEY=your_key_here
"""

import time
import requests
from pathlib import Path

FREESOUND_API = "https://freesound.org/apiv2"


def generate_soundtrack(style, video_duration_secs, anthropic_key, freesound_key,
                        output_dir, log_fn=print):
    """
    Retrieve a cinematic soundtrack matched to the video's mood.

    If Freesound key is missing, returns None — video will render without music
    and user can add their own track in post.
    """
    if not freesound_key:
        log_fn("  ⚠ No FREESOUND_API_KEY — video will render without music")
        log_fn("    Add your own soundtrack in post-production")
        return None

    music_config = style.get("music", {})
    mood         = music_config.get("mood", "cinematic tension")
    style_desc   = music_config.get("style", "orchestral minimal")

    query = f"{style_desc} {mood} music cinematic"

    log_fn(f"  🎵 Searching Freesound for: {query[:50]}...")

    try:
        # Search for sounds
        r = requests.get(
            f"{FREESOUND_API}/search/text/",
            params={
                "query": query,
                "token": freesound_key,
                "filter": "tag:cinematic OR tag:ambient OR tag:music",
                "fields": "id,name,previews",
                "page_size": 1
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        
        results = data.get("results", [])
        if not results:
            log_fn("  ⚠ Freesound returned no exact match, trying broader search...")
            # Fallback search
            r_fallback = requests.get(
                f"{FREESOUND_API}/search/text/",
                params={
                    "query": "cinematic background music",
                    "token": freesound_key,
                    "fields": "id,name,previews",
                    "page_size": 1,
                    "sort": "rating_desc"
                },
                timeout=30,
            )
            r_fallback.raise_for_status()
            data = r_fallback.json()
            results = data.get("results", [])
            
            if not results:
                log_fn("  ⚠ Freesound returned no results even on fallback")
                return None

        sound = results[0]
        audio_url = sound.get("previews", {}).get("preview-hq-mp3")
        
        if audio_url:
            return _download_audio(audio_url, output_dir, log_fn)
            
        log_fn("  ⚠ No HQ MP3 preview available for the sound.")
        return None

    except Exception as e:
        log_fn(f"  ⚠ Freesound error: {e} — continuing without music")
        return None


def _download_audio(url, output_dir, log_fn):
    """Download the generated audio file."""
    output_path = Path(output_dir) / "soundtrack.mp3"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        log_fn(f"  ✅ Soundtrack downloaded")
        return str(output_path)
    except Exception as e:
        log_fn(f"  ⚠ Soundtrack download failed: {e}")
        return None
