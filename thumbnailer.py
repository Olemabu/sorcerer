"""
SORCERER — Thumbnail Generator & Extractor
============================================
Handles thumbnail creation for the production pipeline.
1. Extracts high-res thumbnails from original YouTube videos.
2. Formats AI-generated MrBeast-style thumbnail blueprints.
"""

import os
import subprocess
from pathlib import Path

def extract_youtube_thumbnail(url, output_dir, video_id="video", log_fn=print):
    """
    Download the highest resolution thumbnail for a YouTube video using yt-dlp.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{video_id}_thumbnail.jpg"

    log_fn("  🖼️  Extracting YouTube thumbnail...")
    cmd = [
        "yt-dlp",
        "--write-thumbnail",
        "--skip-download",
        "-o", str(output_dir / f"{video_id}_thumbnail.%(ext)s"),
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # yt-dlp might save as .webp or .jpg depending on availability
        candidates = list(output_dir.glob(f"{video_id}_thumbnail.*"))
        if candidates:
            log_fn(f"  ✅  Thumbnail extracted → {candidates[0].name}")
            return str(candidates[0])
            
        log_fn(f"  ⚠ Thumbnail extraction failed or not found: {result.stderr[-200:]}")
        return None
    except Exception as e:
        log_fn(f"  ⚠ Thumbnail extraction error: {e}")
        return None


def format_thumbnail_plan(script):
    """
    Takes the thumbnail JSON from the generated script and formats it 
    into a readable blueprint for the user.
    """
    th = script.get("thumbnail")
    if not th:
        return "No thumbnail data generated."

    plan = (
        f"🖼️ <b>THUMBNAIL BLUEPRINT</b>\n"
        f"─────────────────────────\n"
        f"<b>Text Overlay:</b> {th.get('text_overlay', '')}\n"
        f"<b>Main Image:</b> {th.get('main_image', '')}\n"
        f"<b>Background:</b> {th.get('background', '')}\n"
        f"<b>Colors:</b> {th.get('color_scheme', '')}\n\n"
        f"<b>Face Expression:</b> {th.get('face_expression', '')}\n"
        f"<b>Mobile Test:</b> {th.get('mobile_test', '')}\n\n"
        f"🎨 <b>Image Gen Prompt (Midjourney/Gemini):</b>\n"
        f"<code>{th.get('gemini_prompt', 'N/A')}</code>\n"
    )
    return plan
