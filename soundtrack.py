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
            return _download_audio(audio_url, output_dir, "soundtrack.mp3", log_fn)
            
        log_fn("  ⚠ No HQ MP3 preview available for the sound.")
        return None

    except Exception as e:
        log_fn(f"  ⚠ Freesound error: {e} — continuing without music")
        return None


def download_sfx_moments(sfx_moments, freesound_key, output_dir, log_fn=print):
    """
    Download a list of spot sound effects from Freesound.
    Each moment in sfx_moments should have 'timestamp' and 'search_keyword'.
    """
    if not freesound_key or not sfx_moments:
        return []

    sfx_dir = Path(output_dir) / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)

    results = []
    log_fn(f"  🔊 Downloading {len(sfx_moments)} spot sound effects...")

    for i, moment in enumerate(sfx_moments):
        query = moment.get("search_keyword") or moment.get("sound", "digital whoosh")
        ts    = moment.get("timestamp", "0:00")
        
        log_fn(f"  🔊 [{i+1}/{len(sfx_moments)}] searching: {query}...", )
        
        try:
            r = requests.get(
                f"{FREESOUND_API}/search/text/",
                params={
                    "query": query,
                    "token": freesound_key,
                    "filter": "tag:sfx OR tag:foley OR tag:field-recording",
                    "fields": "id,name,previews",
                    "page_size": 1,
                    "sort": "rating_desc"
                },
                timeout=20,
            )
            r.raise_for_status()
            data = r.json().get("results", [])
            
            if not data:
                log_fn(" no results")
                continue

            audio_url = data[0].get("previews", {}).get("preview-hq-mp3")
            if not audio_url:
                log_fn(" no HQ MP3")
                continue

            filename = f"sfx_{i}_{query[:15].replace(' ','_')}.mp3"
            path = _download_audio(audio_url, str(sfx_dir), filename, log_fn=lambda x: None)
            
            if path:
                results.append({
                    "path": path,
                    "timestamp": ts,
                    "sound": moment.get("sound")
                })
                log_fn(" ✓")
            else:
                log_fn(" download failed")

        except Exception as e:
            log_fn(f" error: {e}")
        
        time.sleep(0.3) # Be gentle with Freesound API

    return results


def _download_audio(url, output_dir, filename, log_fn):
    """Download the generated audio file."""
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if log_fn:
            log_fn(f"  ✅ Audio downloaded to {filename}")
        return str(output_path)
    except Exception as e:
        if log_fn:
            log_fn(f"  ⚠ Audio download failed: {e}")
        return None
