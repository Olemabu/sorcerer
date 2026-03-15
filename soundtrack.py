"""
SORCERER — Soundtrack
======================
Generates a mood-matched cinematic soundtrack using Suno API.

For documentary style: orchestral tension, dark ambient,
occasional ironic contrast moments (upbeat music under
apocalyptic narration = comedy gold).

Cost: ~$0.03 per track on Suno Pro ($8/mo flat)

Setup:
  1. Go to suno.com → Sign up → Pro plan ($8/mo)
  2. Go to Settings → API → Generate key
  3. Add to .env: SUNO_API_KEY=your_key_here
"""

import time
import requests
from pathlib import Path

SUNO_API = "https://studio-api.suno.ai/api/external"


def generate_soundtrack(style, video_duration_secs, anthropic_key, suno_key,
                        output_dir, log_fn=print):
    """
    Generate a cinematic soundtrack matched to the video's mood.

    If Suno key is missing, returns None — video will render without music
    and user can add their own track in post.
    """
    if not suno_key:
        log_fn("  ⚠ No SUNO_API_KEY — video will render without music")
        log_fn("    Add your own soundtrack in post-production")
        return None

    music_config = style.get("music", {})
    mood         = music_config.get("mood", "cinematic tension")
    tempo        = music_config.get("tempo", "slow build")
    style_desc   = music_config.get("style", "orchestral minimal")

    # Generate a prompt for Suno
    duration_mins = round(video_duration_secs / 60, 1)
    prompt = (
        f"{style_desc}, {mood}, {tempo}. "
        f"Instrumental only, no vocals. "
        f"Cinematic documentary soundtrack. "
        f"Should feel like a {duration_mins}-minute journey. "
        f"Hans Zimmer meets dark ambient. "
        f"Builds in intensity over time. "
        f"Occasional moments of ironic lightness."
    )

    log_fn(f"  🎵 Generating soundtrack: {prompt[:80]}...")

    try:
        # Submit generation
        r = requests.post(
            f"{SUNO_API}/generate/",
            headers={
                "Authorization": f"Bearer {suno_key}",
                "Content-Type":  "application/json",
            },
            json={
                "prompt":              prompt,
                "make_instrumental":   True,
                "wait_audio":          False,
            },
            timeout=30,
        )
        r.raise_for_status()
        data     = r.json()
        clip_ids = [item["id"] for item in data if item.get("id")]

        if not clip_ids:
            log_fn("  ⚠ Suno returned no clip IDs")
            return None

        clip_id = clip_ids[0]

        # Poll for completion
        for attempt in range(30):
            time.sleep(10)
            status_r = requests.get(
                f"{SUNO_API}/feed/?ids={clip_id}",
                headers={"Authorization": f"Bearer {suno_key}"},
                timeout=15,
            )
            status_r.raise_for_status()
            items  = status_r.json()
            status = items[0].get("status") if items else None

            if status == "complete":
                audio_url = items[0].get("audio_url")
                if audio_url:
                    return _download_audio(audio_url, output_dir, log_fn)
                break
            elif status == "error":
                log_fn("  ⚠ Suno generation failed")
                return None

        log_fn("  ⚠ Suno timed out — continuing without music")
        return None

    except Exception as e:
        log_fn(f"  ⚠ Suno error: {e} — continuing without music")
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
