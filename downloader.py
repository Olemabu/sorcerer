"""
SORCERER — YouTube Downloader
===============================
Downloads YouTube videos using yt-dlp.

Functions:
  get_video_info(url)                — metadata only, no download
  download_video(url, output_dir)    — best quality mp4, returns path
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime


MAX_DURATION_SECS = 1800   # 30 minutes — skip livestreams


def get_video_info(url):
    """
    Fetch video metadata without downloading.

    Returns dict:
        title, channel, duration (secs), description, view_count, like_count,
        upload_date, thumbnail, video_id
    """
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-playlist",
        url,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {"_error": result.stderr.strip()[-300:]}

        data = json.loads(result.stdout)
        return {
            "video_id":    data.get("id", ""),
            "title":       data.get("title", ""),
            "channel":     data.get("channel", data.get("uploader", "")),
            "duration":    data.get("duration", 0),
            "description": data.get("description", "")[:1000],
            "view_count":  data.get("view_count", 0),
            "like_count":  data.get("like_count", 0),
            "upload_date": data.get("upload_date", ""),
            "thumbnail":   data.get("thumbnail", ""),
        }
    except subprocess.TimeoutExpired:
        return {"_error": "Timed out fetching video info"}
    except Exception as e:
        return {"_error": str(e)}


def download_video(url, output_dir, max_duration_secs=MAX_DURATION_SECS, log_fn=print):
    """
    Download a YouTube video as mp4.

    Args:
        url                : YouTube URL
        output_dir         : directory to save into
        max_duration_secs  : skip videos longer than this (default 30 min)
        log_fn             : logging function

    Returns:
        (path, info) on success — path to downloaded mp4, info dict
        (None, error_msg) on failure
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Get info first to check duration
    log_fn("  📥  Fetching video info...")
    info = get_video_info(url)
    if info.get("_error"):
        return None, f"Could not fetch info: {info['_error']}"

    duration = info.get("duration", 0)
    if duration > max_duration_secs:
        return None, (
            f"Video too long: {duration // 60}m {duration % 60}s "
            f"(max {max_duration_secs // 60}m). "
            f"Use a shorter video or increase the limit."
        )

    log_fn(f"  📥  Downloading: {info['title'][:50]}... ({duration // 60}m {duration % 60}s)")

    # 2. Download
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    vid_id   = info.get("video_id", "video")
    filename = f"{ts}_{vid_id}.mp4"
    out_path = output_dir / filename

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(out_path),
        url,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            return None, f"Download failed: {result.stderr.strip()[-300:]}"

        # yt-dlp may adjust the filename — find the actual file
        if out_path.exists():
            log_fn(f"  ✅  Downloaded → {out_path.name}")
            return str(out_path), info

        # Check for slightly different name (yt-dlp sometimes appends)
        candidates = list(output_dir.glob(f"{ts}_{vid_id}*"))
        if candidates:
            actual = str(candidates[0])
            log_fn(f"  ✅  Downloaded → {candidates[0].name}")
            return actual, info

        return None, "Download appeared to succeed but file not found"

    except subprocess.TimeoutExpired:
        return None, "Download timed out (10 min limit)"
    except Exception as e:
        return None, str(e)
