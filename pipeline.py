"""
SORCERER — Documentary Pipeline
=================================
One function. Full cinematic documentary. No camera needed.

Sequence:
  1. Intelligence brief (comment analysis, angle, audience)
  2. Script (Claude Opus — funny, gripping, narration-style)
  3. Shot list (Claude Sonnet — visual direction per section)
  4. Narration audio (ElevenLabs — your cloned voice)
  5. B-roll footage (Pexels — free) + hero shots (Kling — cinematic)
  6. Soundtrack (Suno — mood-matched cinematic)
  7. Composite (FFmpeg — cinematic grade, grain, letterbox)
  8. Captions (Claude Sonnet — platform-native per SM)
  9. Clips (FFmpeg — 9:16 vertical + 16:9 landscape)
  10. Publish (YouTube, Facebook, Instagram, TikTok, Telegram)

Total cost: ~$0.58/video
Total time: ~15-25 minutes per video (mostly API wait time)
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime


def produce(
    video,
    signal,
    baseline,
    comments,
    config,
    style_name="cinematic",
    log_fn=print,
):
    """
    Full documentary production pipeline.

    Args:
        video       : spiking competitor video dict
        signal      : signal dict (level, multiplier, window)
        baseline    : channel baseline dict
        comments    : list of comment dicts
        config      : dict of all API keys and toggles
        style_name  : "cinematic" (only style for now)
        log_fn      : logging function

    Returns:
        dict with paths to final video, clips, script, and publish results
    """
    anthropic_key  = config.get("anthropic_key", "")
    elevenlabs_key = config.get("elevenlabs_key", "")
    voice_id       = config.get("elevenlabs_voice_id", "")
    pexels_key     = config.get("pexels_key", "")
    kling_key      = config.get("kling_key", "")
    suno_key       = config.get("suno_key", "")

    # Output directory for this video
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_slug = video.get("id", "video")
    output_dir = Path(config.get("data_dir", ".")) / "productions" / f"{ts}_{video_slug}"
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "video_id":    video.get("id"),
        "title":       None,
        "script_file": None,
        "audio_file":  None,
        "video_file":  None,
        "clips":       {},
        "published":   {},
        "output_dir":  str(output_dir),
    }

    # Load style config
    style = _load_style(style_name)

    log_fn(f"\n{'═'*60}")
    log_fn(f"  🧙 SORCERER — DOCUMENTARY PIPELINE")
    log_fn(f"{'═'*60}")
    log_fn(f"  Source : {video['channel_title']}: {video['title'][:50]}")
    log_fn(f"  Signal : {signal['level']} {signal['multiplier']}× baseline")
    log_fn(f"  Style  : {style_name}")
    log_fn(f"  Output : {output_dir}")
    log_fn(f"{'─'*60}")

    # ── 1. INTELLIGENCE ──────────────────────────────────────────────────────
    log_fn("\n  [1/9] INTELLIGENCE BRIEF")
    from intelligence import analyse
    intel = analyse(video, signal, baseline, comments, anthropic_key)
    if intel and not intel.get("_error"):
        log_fn(f"  ✓ Topic angle: {intel.get('my_video_angle','')[:60]}")
    else:
        log_fn("  ⚠ Intelligence failed — proceeding with basic data")
        intel = {}

    # ── 2. SCRIPT ────────────────────────────────────────────────────────────
    log_fn("\n  [2/9] SCRIPT GENERATION (Claude Opus)")
    from scriptwriter import generate_script, save_script
    script = generate_script(video, signal, baseline, comments, intel, anthropic_key)

    if not script or script.get("_error"):
        log_fn(f"  ❌ Script generation failed: {script.get('_error') if script else 'no response'}")
        return results

    results["title"] = script.get("title", video["title"])
    log_fn(f"  ✓ Title: {results['title'][:60]}")
    log_fn(f"  ✓ Funniest line: \"{script.get('funniest_line','')[:80]}\"")

    script_file = save_script(script, video, str(output_dir))
    results["script_file"] = script_file
    log_fn(f"  ✓ Script saved: {script_file}")

    # ── 3. SHOT LIST ─────────────────────────────────────────────────────────
    log_fn("\n  [3/9] VISUAL DIRECTION (shot list)")
    from visual_director import build_shot_list
    shot_list = build_shot_list(script, anthropic_key, log_fn)
    log_fn(f"  ✓ {len(shot_list)} sections planned")

    # ── 4. NARRATION ─────────────────────────────────────────────────────────
    log_fn("\n  [4/9] NARRATION (ElevenLabs)")
    if elevenlabs_key:
        from narrator import narrate_full_script
        narration_data = narrate_full_script(
            script, voice_id, elevenlabs_key, str(output_dir), log_fn
        )
        if narration_data and narration_data.get("master_audio"):
            results["audio_file"] = narration_data["master_audio"]
            dur = narration_data.get("total_duration_secs", 0)
            log_fn(f"  ✓ Narration complete: {dur/60:.1f} min")
        else:
            log_fn("  ⚠ Narration failed — video will render silent")
            narration_data = {"sections": [], "total_duration_secs": 900}
    else:
        log_fn("  ⚠ No ElevenLabs key — script only mode")
        log_fn("    Record narration yourself using the script file")
        narration_data = {"sections": [], "total_duration_secs": 900}

    # If no narration, skip to script-only output
    if not elevenlabs_key:
        log_fn(f"\n{'─'*60}")
        log_fn("  📄 SCRIPT-ONLY MODE (no audio/video generated)")
        log_fn(f"  Script: {script_file}")
        log_fn(f"{'─'*60}\n")
        return results

    # ── 5. FOOTAGE ───────────────────────────────────────────────────────────
    log_fn("\n  [5/9] FOOTAGE (Pexels + Kling AI)")
    from visual_director import fetch_all_footage
    footage_map = fetch_all_footage(
        shot_list, pexels_key, kling_key, str(output_dir), log_fn
    )
    log_fn(f"  ✓ Footage fetched for {len(footage_map)} sections")

    # ── 6. SOUNDTRACK ────────────────────────────────────────────────────────
    log_fn("\n  [6/9] SOUNDTRACK (Suno)")
    from soundtrack import generate_soundtrack
    soundtrack_path = generate_soundtrack(
        style,
        narration_data.get("total_duration_secs", 900),
        anthropic_key,
        suno_key,
        str(output_dir),
        log_fn,
    )

    # ── 7. COMPOSITE ─────────────────────────────────────────────────────────
    log_fn("\n  [7/9] COMPOSITING (FFmpeg)")
    from compositor import composite_full_video
    final_video = composite_full_video(
        narration_data, footage_map, soundtrack_path,
        style, str(output_dir), log_fn
    )

    if not final_video:
        log_fn("  ❌ Compositing failed")
        return results

    results["video_file"] = final_video
    log_fn(f"  ✓ Video ready: {final_video}")

    # ── 8. CAPTIONS ──────────────────────────────────────────────────────────
    log_fn("\n  [8/9] CAPTIONS (Claude Sonnet — platform native)")
    from publisher.captions import generate_captions
    captions = generate_captions(
        results["title"], script, intel, signal, anthropic_key
    )
    log_fn("  ✓ Platform captions generated")

    # ── 9. CLIPS + PUBLISH ───────────────────────────────────────────────────
    log_fn("\n  [9/9] CLIPS + PUBLISH")
    from publisher.clipper import prepare_all_clips
    video_duration_mins = narration_data.get("total_duration_secs", 900) / 60
    clips = prepare_all_clips(
        final_video, script, video_duration_mins, str(output_dir), anthropic_key, log_fn
    )
    results["clips"] = clips

    if config.get("publish_enabled"):
        from publisher import publish_all, build_config_from_env
        pub_config = build_config_from_env()
        youtube_url = f"https://youtube.com/watch?v=pending"

        publish_results = publish_all(
            master_video_path = final_video,
            clips             = clips,
            captions          = captions,
            youtube_url       = youtube_url,
            config            = pub_config,
            log_fn            = log_fn,
        )
        results["published"] = publish_results

    # ── DONE ─────────────────────────────────────────────────────────────────
    log_fn(f"\n{'═'*60}")
    log_fn(f"  🧙 SORCERER — PRODUCTION COMPLETE")
    log_fn(f"{'─'*60}")
    log_fn(f"  Title   : {results['title']}")
    log_fn(f"  Video   : {results.get('video_file','—')}")
    log_fn(f"  Script  : {results.get('script_file','—')}")
    log_fn(f"{'═'*60}\n")

    return results


def _load_style(style_name):
    """Load style config from JSON file."""
    import json
    style_path = Path(__file__).parent / "styles" / f"{style_name}.json"
    if style_path.exists():
        return json.loads(style_path.read_text())
    # Fallback minimal style
    return {
        "color":   {"background": "#000000", "title_primary": "#FFFFFF", "title_accent": "#FF3355"},
        "effects": {"film_grain": True, "vignette": True, "letterbox": True, "slow_zoom_broll": True},
        "music":   {"duck_level_db": -18, "full_level_db": -8},
    }


def build_config_from_env():
    """Build production config from environment variables."""
    return {
        "anthropic_key":        os.getenv("ANTHROPIC_API_KEY", ""),
        "elevenlabs_key":       os.getenv("ELEVENLABS_API_KEY", ""),
        "elevenlabs_voice_id":  os.getenv("ELEVENLABS_VOICE_ID", ""),
        "pexels_key":           os.getenv("PEXELS_API_KEY", ""),
        "kling_key":            os.getenv("KLING_API_KEY", ""),
        "suno_key":             os.getenv("SUNO_API_KEY", ""),
        "data_dir":             os.getenv("SORCERER_DATA_DIR", "."),
        "publish_enabled":      os.getenv("AUTO_PUBLISH", "false").lower() == "true",
    }
