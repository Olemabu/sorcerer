"""
SORCERER — Clipper
================
Extracts the best 60-90 second clip from the full video.
Renders it in multiple aspect ratios for each platform.

Clip selection is NOT random — Claude identifies the highest-density
segment based on: hook language, comment bait moment, or the single
most counter-intuitive claim in the script.

Renders:
  clip_vertical.mp4    9:16  — TikTok, Facebook Reels
  clip_landscape.mp4   16:9  — Twitter/X, YouTube Shorts preview

Requires: ffmpeg installed on system
  Mac:    brew install ffmpeg
  Linux:  apt install ffmpeg
  Railway: add to nixpacks.toml (auto-handled)
"""

import os
import json
import subprocess
import requests
from pathlib import Path

CLAUDE_MODEL  = "claude-sonnet-4-6"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# Platform clip specs
CLIP_SPECS = {
    "vertical":  {"w": 1080, "h": 1920, "ratio": "9:16", "max_secs": 89},
    "landscape": {"w": 1920, "h": 1080, "ratio": "16:9", "max_secs": 139},
}

TARGET_CLIP_SECS = 75   # aim for 75 seconds — fits all platforms


def select_clip_segment(script, video_duration_mins, anthropic_key):
    """
    Ask Claude which timestamp range has the highest viral density.
    Returns (start_secs, end_secs).
    """
    if not anthropic_key or not script:
        # Fallback: use first 75 seconds after the hook
        return (45, 45 + TARGET_CLIP_SECS)

    sections       = script.get("sections", [])
    comment_baits  = script.get("comment_bait_moments", [])
    pain_map       = script.get("pain_profit_map", [])

    section_block = "\n".join(
        f"[{s.get('timestamp','?')}] {s.get('name','')} — {s.get('pain_point_addressed','')}"
        for s in sections
    )

    bait_block = "\n".join(
        f"{b.get('timestamp','?')} — \"{b.get('line','')}\" ({b.get('why_it_works','')})"
        for b in comment_baits
    )

    prompt = f"""A YouTube video is {video_duration_mins} minutes long.
I need to extract the BEST 75-second clip for TikTok/Reels — the segment most likely to go viral standalone.

VIDEO STRUCTURE:
{section_block}

COMMENT BAIT MOMENTS (highest engagement):
{bait_block}

Pick the 75-second window that:
1. Can be understood without watching the full video
2. Contains the most surprising or controversial moment
3. Creates maximum FOMO — makes people want to watch the full video
4. Has a natural start and end point

Return ONLY valid JSON:
{{
  "start_seconds": <integer>,
  "end_seconds": <integer>,
  "reason": "one sentence on why this segment"
}}"""

    try:
        r = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key":         anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      CLAUDE_MODEL,
                "max_tokens": 200,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        r.raise_for_status()
        raw  = r.json()["content"][0]["text"].strip()
        raw  = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        return (int(data["start_seconds"]), int(data["end_seconds"]))
    except Exception:
        return (45, 45 + TARGET_CLIP_SECS)


def check_ffmpeg():
    """Returns True if ffmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"],
                       capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def extract_clip(source_path, start_secs, end_secs, output_path, ratio="landscape"):
    """
    Extract and reformat a clip using ffmpeg.

    ratio: "landscape" (16:9) or "vertical" (9:16)
    """
    if not check_ffmpeg():
        return False, "ffmpeg not found — install with: brew install ffmpeg"

    spec     = CLIP_SPECS.get(ratio, CLIP_SPECS["landscape"])
    duration = end_secs - start_secs
    w, h     = spec["w"], spec["h"]

    # For vertical: crop center of landscape video, scale to 9:16
    if ratio == "vertical":
        vf = (
            f"crop=ih*9/16:ih,"          # crop to 9:16 from center
            f"scale={w}:{h},"            # scale to target
            f"setsar=1"
        )
    else:
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1"

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_secs),
        "-i", str(source_path),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return False, result.stderr[-500:]
        return True, str(output_path)
    except subprocess.TimeoutExpired:
        return False, "ffmpeg timed out"
    except Exception as e:
        return False, str(e)


def prepare_all_clips(source_path, script, video_duration_mins, output_dir, anthropic_key, log_fn=print):
    """
    Master function — selects segment, renders all format variants.

    Returns dict:
    {
      "start_secs": int,
      "end_secs": int,
      "clip_vertical": "/path/to/clip_vertical.mp4" or None,
      "clip_landscape": "/path/to/clip_landscape.mp4" or None,
      "reason": "why this segment was chosen",
    }
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log_fn("  ✂️  Selecting best clip segment...")
    start, end = select_clip_segment(script, video_duration_mins, anthropic_key)
    log_fn(f"  ✂️  Clip window: {start}s – {end}s ({end - start}s)")

    results = {
        "start_secs":      start,
        "end_secs":        end,
        "clip_vertical":   None,
        "clip_landscape":  None,
        "reason":          "AI-selected highest-density segment",
    }

    if not check_ffmpeg():
        log_fn("  ⚠️  ffmpeg not installed — skipping clip renders")
        log_fn("      Install: brew install ffmpeg  (Mac) / apt install ffmpeg  (Linux)")
        return results

    for ratio in ["vertical", "landscape"]:
        out_path = output_dir / f"clip_{ratio}.mp4"
        log_fn(f"  🎬  Rendering {ratio} clip ({CLIP_SPECS[ratio]['ratio']})...")
        ok, msg = extract_clip(source_path, start, end, out_path, ratio)
        if ok:
            results[f"clip_{ratio}"] = str(out_path)
            log_fn(f"  ✅  {ratio} clip → {out_path}")
        else:
            log_fn(f"  ⚠️  {ratio} clip failed: {msg}")

    return results
