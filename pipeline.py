"""
SORCERER — Documentary Pipeline
=================================
One function. Full cinematic documentary. No camera needed.

Sequence:
  1.  Intelligence brief (comment analysis, angle, audience)
  2.  Script (Claude Opus — funny, gripping, narration-style)
  3.  AI Director (Claude Opus — emotional clusters, colour narrative)
  4.  Shot list (Claude Sonnet — visual direction per section)
  5.  Narration audio (Edge TTS — your voice)
  6.  Board Animator (Remotion — whiteboard/chalkboard motion graphics)
  7.  B-roll footage (Pexels — free) + hero shots (Kling — cinematic)
  8.  Soundtrack + SFX (Freesound — mood-matched cinematic)
  9.  Composite (Remotion primary → FFmpeg fallback)
  10. Captions (Claude Sonnet — platform-native per SM)
  11. Clips (FFmpeg — 9:16 vertical + 16:9 landscape)
  12. Publish (YouTube, Facebook, Instagram, TikTok, Telegram)

Total cost: ~$0.73/video (with Director + Board Animator)
Total time: ~15-25 minutes per video (mostly API wait time)
"""

import os
import json
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


def _check_node_available():
    """Check if Node.js is installed for Remotion rendering."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def produce(
    video,
    signal,
    baseline,
    comments,
    config,
    style_name="cinematic",
    log_fn=print,
    is_exact_text=False,
    aspect_ratio="16:9",
    vet=False,
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
        vet         : whether to run the Director vetting loop

    Returns:
        dict with paths to final video, clips, script, and publish results
    """
    anthropic_key  = config.get("anthropic_key", "")
    voice_id       = config.get("edge_tts_voice", "en-US-ChristopherNeural")
    pexels_key     = config.get("pexels_key", "")
    kling_key      = config.get("kling_key", "")
    freesound_key  = config.get("freesound_key", "")

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
    log_fn("\n  [1/12] INTELLIGENCE BRIEF")
    from intelligence import analyse
    intel = analyse(video, signal, baseline, comments, anthropic_key)
    if intel and not intel.get("_error"):
        log_fn(f"  ✓ Topic angle: {intel.get('my_video_angle','')[:60]}")
    else:
        log_fn("  ⚠ Intelligence failed — proceeding with basic data")
        intel = {}

    # ── 2. SCRIPT ────────────────────────────────────────────────────────────
    log_fn("\n  [2/12] SCRIPT GENERATION (Claude Opus)")
    from scriptwriter import generate_script, save_script
    script = generate_script(video, signal, baseline, comments, intel, anthropic_key, is_exact_text=is_exact_text)

    if not script or script.get("_error"):
        log_fn(f"  ❌ Script generation failed: {script.get('_error') if script else 'no response'}")
        return results

    results["title"] = script.get("title", video["title"])
    log_fn(f"  ✓ Title: {results['title'][:60]}")
    log_fn(f"  ✓ Funniest line: \"{script.get('funniest_line','')[:80]}\"")

    script_file = save_script(script, video, str(output_dir))
    results["script_file"] = script_file
    log_fn(f"  ✓ Script saved: {script_file}")

    # ── THUMBNAIL ────────────────────────────────────────────────────────────
    log_fn("\n  [+] THUMBNAIL PREPARATION")
    from thumbnailer import extract_youtube_thumbnail, format_thumbnail_plan
    try:
        if video.get("id") and video.get("id") not in ("topic", "concept"):
            yt_url = f"https://youtube.com/watch?v={video['id']}"
            thumb_path = extract_youtube_thumbnail(yt_url, str(output_dir), video['id'], log_fn)
            results["thumbnail_file"] = thumb_path

        results["thumbnail_plan"] = format_thumbnail_plan(script)
    except Exception as e:
        log_fn(f"  ⚠ Thumbnail step failed: {e}")

    # ── 3. AI DIRECTOR ───────────────────────────────────────────────────────
    log_fn("\n  [3/12] AI DIRECTOR (Claude Opus)")
    direction = None
    try:
        from director import direct, vet_direction, apply_fixes
        direction = direct(
            script, style="hybrid", target_culture="global",
            aspect_ratio=aspect_ratio,
            anthropic_key=anthropic_key, log_fn=log_fn,
        )
        if direction and not direction.get("_error"):
            log_fn(f"  ✓ Vision: {direction.get('direction_title', '')[:60]}")
            
            # --- VETTING LOOP ---
            if vet:
                report = vet_direction(script, direction, anthropic_key, log_fn)
                if report:
                    log_fn(f"  🎬 EP Score: {report.get('overall_quality',0)}/10")
                    for flaw in report.get("lethal_flaws", []):
                        log_fn(f"  🚩 {flaw}")
                    direction = apply_fixes(direction, report, anthropic_key, log_fn)

            rep = direction.get("replayability_score", {})
            log_fn(f"  ✓ Replayability: {rep.get('score', '?')}/10")
            results["direction"] = direction
        else:
            log_fn(f"  ⚠ Director failed: {direction.get('_error', 'unknown') if direction else 'no response'}")
            direction = None
    except Exception as e:
        log_fn(f"  ⚠ Director step failed: {e}")
        direction = None

    # ── 4. SHOT LIST ─────────────────────────────────────────────────────────
    log_fn("\n  [4/12] VISUAL DIRECTION (shot list)")
    from visual_director import build_shot_list
    shot_list = build_shot_list(script, anthropic_key, log_fn)
    log_fn(f"  ✓ {len(shot_list)} sections planned")

    # ── 5. NARRATION ─────────────────────────────────────────────────────────
    log_fn("\n  [5/12] NARRATION (Edge TTS)")
    from narrator import narrate_full_script
    narration_data = narrate_full_script(
        script, voice_id, str(output_dir), log_fn
    )
    if narration_data and narration_data.get("master_audio"):
        results["audio_file"] = narration_data["master_audio"]
        dur = narration_data.get("total_duration_secs", 0)
        log_fn(f"  ✓ Narration complete: {dur/60:.1f} min")
    else:
        log_fn("  ⚠ Narration failed — video will render silent")
        narration_data = {"sections": [], "total_duration_secs": 900}

    # ── 6. BOARD ANIMATOR ────────────────────────────────────────────────────
    log_fn("\n  [6/12] BOARD ANIMATOR (motion graphics)")
    board_actions = None
    remotion_dir  = None
    try:
        from board_animator import assign_board_actions, generate_remotion_project

        # Step 6a: AI assigns board actions to every beat of the script
        board_actions = assign_board_actions(
            script, direction, anthropic_key, log_fn
        )
        timeline_len = len(board_actions.get("board_timeline", []))
        cast_len     = len(board_actions.get("png_cast", []))
        log_fn(f"  ✓ Board actions: {timeline_len} beats, {cast_len} characters")

        # Step 6b: Generate the Remotion project
        audio_path = narration_data.get("master_audio", "")
        
        from resolution import get_resolution
        width, height, res_name = get_resolution(aspect_ratio)
        log_fn(f"  📐 Aspect Ratio: {aspect_ratio} ({width}x{height})")
        
        remotion_dir = generate_remotion_project(
            script, direction, board_actions,
            audio_path, str(output_dir), log_fn,
            width=width, height=height
        )
        log_fn(f"  ✓ Remotion project: {remotion_dir}")
        results["remotion_dir"] = remotion_dir

    except Exception as e:
        log_fn(f"  ⚠ Board animator failed: {e} — will fall back to FFmpeg")

    # ── 7. FOOTAGE ───────────────────────────────────────────────────────────
    log_fn("\n  [7/12] FOOTAGE (Pexels + Kling AI)")
    from visual_director import fetch_all_footage
    footage_map = fetch_all_footage(
        shot_list, pexels_key, kling_key, str(output_dir), log_fn
    )
    log_fn(f"  ✓ Footage fetched for {len(footage_map)} sections")

    # ── 8. SOUNDTRACK + SFX ──────────────────────────────────────────────────
    log_fn("\n  [8/12] SOUNDTRACK + SFX (Freesound)")
    from soundtrack import generate_soundtrack, download_sfx_moments
    
    soundtrack_path = generate_soundtrack(
        style,
        narration_data.get("total_duration_secs", 900),
        anthropic_key,
        freesound_key,
        str(output_dir),
        log_fn,
    )
    
    sfx_data = []
    if direction and "sound_architecture" in direction:
        sfx_moments = direction["sound_architecture"].get("sfx_moments", [])
        if sfx_moments:
            sfx_data = download_sfx_moments(
                sfx_moments, freesound_key, str(output_dir), log_fn
            )

    # ── 9. COMPOSITE ─────────────────────────────────────────────────────────
    # PRIMARY: Remotion board animation render (if project was generated + Node available)
    # FALLBACK: FFmpeg compositor with b-roll footage
    final_video = None

    if remotion_dir and _check_node_available():
        log_fn("\n  [9/12] RENDERING (Remotion — motion graphics)")
        try:
            from board_animator import render_video
            render_output = str(output_dir / "board_video.mp4")
            ok = render_video(remotion_dir, render_output, log_fn)
            if ok and Path(render_output).exists():
                # Mix soundtrack + SFX into the Remotion render using unified mixer
                if (soundtrack_path and Path(soundtrack_path).exists()) or sfx_data:
                    log_fn("  🎵 Mixing audio into board animation...")
                    from compositor import mix_audio_layers
                    
                    mixed_output = str(output_dir / "final_video.mp4")
                    ok = mix_audio_layers(
                        video_path=render_output,
                        narration_path=None, # Already in render_output
                        soundtrack_path=soundtrack_path,
                        sfx_data=sfx_data,
                        style=style,
                        output_path=mixed_output,
                        log_fn=log_fn
                    )
                    
                    if ok and Path(mixed_output).exists():
                        final_video = mixed_output
                    else:
                        final_video = render_output
                else:
                    final_video = render_output
                log_fn(f"  ✓ Board animation rendered: {final_video}")
        except Exception as e:
            log_fn(f"  ⚠ Remotion render failed: {e} — falling back to FFmpeg")

    if not final_video:
        log_fn("\n  [9/12] COMPOSITING (FFmpeg — b-roll fallback)")
        from compositor import composite_full_video
        final_video = composite_full_video(
            narration_data, footage_map, soundtrack_path,
            style, str(output_dir), sfx_data=sfx_data, log_fn=log_fn
        )

    if not final_video:
        log_fn("  ❌ All compositing methods failed")
        return results

    results["video_file"] = final_video
    log_fn(f"  ✓ Video ready: {final_video}")

    # ── 10. CAPTIONS ──────────────────────────────────────────────────────────
    log_fn("\n  [10/12] CAPTIONS (Claude Sonnet — platform native)")
    from publisher.captions import generate_captions
    captions = generate_captions(
        results["title"], script, intel, signal, anthropic_key
    )
    log_fn("  ✓ Platform captions generated")

    # ── 11. CLIPS + PUBLISH ───────────────────────────────────────────────────
    log_fn("\n  [11/12] CLIPS + PUBLISH")
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
        "edge_tts_voice":       os.getenv("EDGE_TTS_VOICE", "en-US-ChristopherNeural"),
        "pexels_key":           os.getenv("PEXELS_API_KEY", ""),
        "kling_key":            os.getenv("KLING_API_KEY", ""),
        "freesound_key":             os.getenv("FREESOUND_API_KEY", ""),
        "data_dir":             os.getenv("SORCERER_DATA_DIR", "."),
        "publish_enabled":      os.getenv("AUTO_PUBLISH", "false").lower() == "true",
    }
