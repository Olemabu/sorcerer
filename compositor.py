"""
SORCERER — Compositor
======================
Assembles narration audio + b-roll footage + title cards +
lower thirds + film grain + color grade + soundtrack
into a finished cinematic documentary MP4.

Uses FFmpeg exclusively — no external render service.
Runs on Railway or any Linux server.

Install: apt install ffmpeg (handled by nixpacks.toml)

Pipeline per section:
  1. Trim/loop b-roll clips to match narration duration
  2. Apply color grade (teal-orange LUT or FFmpeg curves)
  3. Apply film grain overlay
  4. Apply letterbox (2.39:1 cinematic ratio)
  5. Apply slow zoom (Ken Burns effect) on still/slow footage
  6. Overlay title cards at correct timestamps
  7. Overlay lower thirds
  8. Mix narration audio with music bed

Final output: 1920×1080 MP4, H.264, AAC, ready to upload
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path


# ── FFmpeg helpers ──────────────────────────────────────────────────────────
def ffmpeg(*args, timeout=300, log_fn=print):
    """Run an FFmpeg command. Returns True on success."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            log_fn(f"  ⚠ FFmpeg error: {result.stderr[-300:]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        log_fn("  ⚠ FFmpeg timed out")
        return False
    except FileNotFoundError:
        log_fn("  ❌ FFmpeg not found — install with: apt install ffmpeg")
        return False


def probe_duration(file_path):
    """Get duration of a media file in seconds."""
    try:
        r = subprocess.run([
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(file_path)
        ], capture_output=True, text=True, timeout=15)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


# ── Section compositor ──────────────────────────────────────────────────────
def composite_section(section_audio, footage, style, work_dir, log_fn=print):
    """
    Composite one script section into a video clip.

    section_audio : path to the narration MP3 for this section
    footage       : dict with clips, title_cards, lower_thirds, visual_treatment
    style         : loaded style JSON dict
    work_dir      : temp directory for intermediate files

    Returns path to the composited MP4, or None on failure.
    """
    work = Path(work_dir)
    name = footage.get("section_name", "section").replace(" ", "_").lower()

    narration_dur = probe_duration(section_audio)
    if narration_dur <= 0:
        narration_dur = footage.get("duration_secs", 30)

    clips  = footage.get("clips", [])
    visual = footage.get("visual_treatment", "slow_broll_narration")

    # ── TITLE CARD sections (no footage) ───────────────────────────────────
    if visual == "black_title_card" or not clips:
        return _make_title_card_section(
            section_audio, footage, style, work, name, narration_dur, log_fn
        )

    # ── B-ROLL sections ─────────────────────────────────────────────────────
    # 1. Build a looped/trimmed b-roll track matching narration duration
    broll_path = work / f"{name}_broll_raw.mp4"
    ok = _build_broll_track(clips, narration_dur, str(broll_path), log_fn)
    if not ok:
        # Fallback to black if no b-roll
        return _make_title_card_section(
            section_audio, footage, style, work, name, narration_dur, log_fn
        )

    # 2. Apply cinematic treatment
    treated_path = work / f"{name}_treated.mp4"
    ok = _apply_cinematic_treatment(
        str(broll_path), str(treated_path), style, visual, log_fn
    )
    if not ok:
        treated_path = broll_path

    # 3. Overlay title cards and lower thirds
    overlay_path = work / f"{name}_overlaid.mp4"
    overlays     = footage.get("title_cards", []) + footage.get("lower_thirds", [])
    if overlays:
        ok = _apply_text_overlays(str(treated_path), overlays, style, str(overlay_path), log_fn)
        if not ok:
            overlay_path = treated_path
    else:
        overlay_path = treated_path

    # 4. Mix in narration audio
    final_path = work / f"{name}_final.mp4"
    ok = ffmpeg(
        "-i", str(overlay_path),
        "-i", section_audio,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(final_path),
        log_fn=log_fn,
    )

    return str(final_path) if ok else None


def _make_title_card_section(audio, footage, style, work, name, duration, log_fn):
    """Generate a black screen title card section."""
    colors      = style.get("color", {})
    typo        = style.get("typography", {})
    bg          = colors.get("background", "#000000")
    fg          = colors.get("title_primary", "#FFFFFF")
    accent      = colors.get("title_accent", "#FF3355")
    font        = typo.get("title_font", "DejaVu-Sans-Bold")
    size        = typo.get("title_size", 72)

    title_cards = footage.get("title_cards", [])
    output      = work / f"{name}_titlecard.mp4"

    if title_cards:
        text = title_cards[0].get("text", "")
        # Escape special chars for FFmpeg
        text_safe = text.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")

        ok = ffmpeg(
            "-f", "lavfi",
            "-i", f"color=c={bg.lstrip('#')}:s=1920x1080:r=25",
            "-i", audio,
            "-vf",
            f"drawtext=text='{text_safe}':fontcolor={fg}:fontsize={size}:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:box=0",
            "-map", "0:v", "-map", "1:a",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-shortest",
            str(output),
            log_fn=log_fn,
        )
    else:
        # Pure black with audio
        ok = ffmpeg(
            "-f", "lavfi",
            "-i", f"color=c=black:s=1920x1080:r=25",
            "-i", audio,
            "-map", "0:v", "-map", "1:a",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-shortest",
            str(output),
            log_fn=log_fn,
        )

    return str(output) if ok else None


def _build_broll_track(clips, target_duration, output_path, log_fn):
    """
    Loop/trim/concatenate b-roll clips to fill the target duration.
    """
    if not clips:
        return False

    work_clips = []
    total_dur  = 0.0

    # Keep adding clips (looping if needed) until we have enough duration
    clip_index = 0
    while total_dur < target_duration:
        clip = clips[clip_index % len(clips)]
        clip_dur = min(
            probe_duration(clip["file"]) or 6.0,
            clip.get("duration", 6.0)
        )
        needed = target_duration - total_dur
        use_dur = min(clip_dur, needed + 0.5)  # slight overshoot, trimmed later

        work_clips.append((clip["file"], use_dur))
        total_dur += use_dur
        clip_index += 1

        if clip_index > 50:  # safety limit
            break

    if not work_clips:
        return False

    # Build FFmpeg concat
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for clip_path, _ in work_clips:
            f.write(f"file '{clip_path}'\n")
        list_file = f.name

    ok = ffmpeg(
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-t", str(target_duration),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an",
        output_path,
        log_fn=log_fn,
    )

    os.unlink(list_file)
    return ok


def _apply_cinematic_treatment(input_path, output_path, style, visual_treatment, log_fn):
    """
    Apply color grade, film grain, letterbox, and slow zoom.
    """
    effects  = style.get("effects", {})
    grain    = effects.get("film_grain", True)
    vignette = effects.get("vignette", True)
    lb       = effects.get("letterbox", True)
    zoom     = effects.get("slow_zoom_broll", True) and visual_treatment not in ("flash_counter_broll", "fast_cut_montage")

    vf_filters = []

    # Color grade — teal-orange cinematic look
    vf_filters.append(
        "curves=r='0/0 0.3/0.25 0.7/0.75 1/1':"
        "g='0/0 0.3/0.28 0.7/0.72 1/1':"
        "b='0/0.05 0.3/0.35 0.7/0.65 1/0.95'"
    )

    # Slow zoom (Ken Burns)
    if zoom:
        vf_filters.append("zoompan=z='min(zoom+0.0008,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080")

    # Vignette
    if vignette:
        intensity = effects.get("vignette_intensity", 0.4)
        vf_filters.append(f"vignette=PI/{1/intensity:.1f}")

    # Film grain
    if grain:
        intensity = effects.get("film_grain_intensity", 0.18)
        vf_filters.append(f"noise=alls={int(intensity*25)}:allf=t")

    # Letterbox (cinematic 2.39:1)
    if lb:
        # Add black bars: 1920x1080 → crop to 2.39:1 then pad back
        vf_filters.append("crop=iw:iw/2.39,pad=1920:1080:0:(oh-ih)/2:black")

    vf_string = ",".join(vf_filters) if vf_filters else "null"

    ok = ffmpeg(
        "-i", input_path,
        "-vf", vf_string,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-an",
        output_path,
        timeout=600,
        log_fn=log_fn,
    )
    return ok


def _apply_text_overlays(input_path, overlays, style, output_path, log_fn):
    """Apply title cards and lower thirds as text overlays."""
    if not overlays:
        return False

    colors = style.get("color", {})
    typo   = style.get("typography", {})
    fg     = colors.get("title_primary", "#FFFFFF").lstrip("#")
    accent = colors.get("title_accent", "#FF3355").lstrip("#")

    drawtext_filters = []
    for overlay in overlays[:4]:  # limit complexity
        text = overlay.get("text", "").replace("'", "\\'").replace(":", "\\:")
        ot   = overlay.get("style", "subtitle")
        size = 42 if ot == "main_title" else 22

        if ot in ("main_title", "title_card"):
            drawtext_filters.append(
                f"drawtext=text='{text}':fontcolor={fg}:fontsize={size}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:box=0"
            )
        else:  # lower third
            drawtext_filters.append(
                f"drawtext=text='{text}':fontcolor={fg}:fontsize={size}:"
                f"x=80:y=h-120:box=1:boxcolor=black@0.7:boxborderw=10"
            )

    vf = ",".join(drawtext_filters) if drawtext_filters else "null"

    ok = ffmpeg(
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-an", output_path,
        log_fn=log_fn,
    )
    return ok


# ── Master compositor ───────────────────────────────────────────────────────
def mix_audio_layers(video_path, narration_path, soundtrack_path, sfx_data,
                     style, output_path, log_fn=print):
    """
    Unified audio mixer for narration, background music, and spot SFX.
    """
    music_cfg = style.get("music", {})
    duck      = music_cfg.get("duck_level_db", -18)

    # 1. Build inputs
    # Input 0:v = video, 0:a = narration (or whatever is in the video file)
    inputs = ["-i", str(video_path)]

    # If narration_path is provided separately (common in Remotion path), we map it
    # But usually, video_path already has the narration baked in for FFmpeg path.
    # To keep it generic, let's assume video_path has the narration at 0:a.

    if soundtrack_path and Path(soundtrack_path).exists():
        inputs += ["-i", str(soundtrack_path)]

    sfx_start_idx = 2 if (soundtrack_path and Path(soundtrack_path).exists()) else 1

    valid_sfx = []
    if sfx_data:
        for sfx in sfx_data:
            if Path(sfx["path"]).exists():
                inputs += ["-i", sfx["path"]]
                valid_sfx.append(sfx)

    # 2. Build filter complex
    filter_parts = []
    amix_inputs  = 1 # Primary narration (0:a)
    
    # Soundtrack
    if soundtrack_path and Path(soundtrack_path).exists():
        filter_parts.append(f"[1:a]volume={duck}dB[music]")
        amix_inputs += 1
        music_label = "[music]"
    else:
        music_label = ""

    # Spot SFX
    sfx_labels = []
    for i, sfx in enumerate(valid_sfx):
        # Convert "MM:SS" or "SS.ms" to milliseconds
        ts = sfx["timestamp"]
        if ":" in ts:
            parts = ts.split(":")
            ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
        else:
            ms = int(float(ts) * 1000)
        
        label = f"[sfx{i}]"
        # adelay=ms|ms is for stereo. If we want to be safe, we can use adelay={ms}:all=1
        filter_parts.append(f"[{sfx_start_idx + i}:a]adelay={ms}|{ms}[sfx_raw{i}]")
        # Optional: Add a small volume boost/cut for SFX if needed
        filter_parts.append(f"[sfx_raw{i}]volume=1.0{label}")
        sfx_labels.append(label)
        amix_inputs += 1

    # 3. Final Mix
    if amix_inputs > 1:
        log_fn(f"  🎵 Mixing soundtrack + {len(sfx_labels)} SFX...")
        mix_str = "[0:a]" + music_label + "".join(sfx_labels)
        # dropout_transition=0.5 for cleaner cuts in short clips
        filter_parts.append(f"{mix_str}amix=inputs={amix_inputs}:duration=first:dropout_transition=0.5[outa]")
        
        ok = ffmpeg(
            *inputs,
            "-filter_complex", ";".join(filter_parts),
            "-map", "0:v",
            "-map", "[outa]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
            timeout=600, log_fn=log_fn,
        )
    else:
        shutil.copy(str(video_path), str(output_path))
        ok = True

    return ok


def composite_full_video(narration_data, footage_map, soundtrack_path,
                          style, output_dir, sfx_data=None, log_fn=print):
    """
    Composite the complete documentary from all sections.
    """
    work_dir = Path(output_dir) / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    narr_sections    = narration_data.get("sections", [])
    section_clips    = []

    log_fn(f"\n  🎬 Compositing {len(narr_sections)} sections...")

    for i, narr in enumerate(narr_sections):
        name = narr.get("name", f"section_{i}")
        log_fn(f"  🎬 [{i+1}/{len(narr_sections)}] {name}...")

        # Match narration section to footage
        footage = next(
            (f for f in footage_map if f.get("section_name") == name),
            {"section_name": name, "clips": [], "title_cards": [], "lower_thirds": []}
        )
        footage["duration_secs"] = narr.get("duration_secs", 30)

        audio = narr.get("audio_file")
        if not audio or not Path(audio).exists():
            log_fn(f" no audio — skipping")
            continue

        clip = composite_section(audio, footage, style, str(work_dir), log_fn)
        if clip:
            section_clips.append(clip)
            log_fn(f" ✓")
        else:
            log_fn(f" ✗ failed")

    if not section_clips:
        log_fn("  ❌ No sections composited — nothing to output")
        return None

    # Concatenate all sections
    log_fn("  🎬 Concatenating sections...")
    raw_video = work_dir / "raw_concat.mp4"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for clip in section_clips:
            f.write(f"file '{clip}'\n")
        list_file = f.name

    ok = ffmpeg(
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        str(raw_video),
        timeout=600, log_fn=log_fn,
    )
    os.unlink(list_file)

    if not ok or not raw_video.exists():
        log_fn("  ❌ Concatenation failed")
        return None

    # Mix in soundtrack and SFX using unified mixer
    final_path = Path(output_dir) / "final_video.mp4"
    ok = mix_audio_layers(
        video_path=raw_video,
        narration_path=None, # Already in raw_video narration track
        soundtrack_path=soundtrack_path,
        sfx_data=sfx_data,
        style=style,
        output_path=final_path,
        log_fn=log_fn
    )

    if ok and final_path.exists():
        size_mb = final_path.stat().st_size / (1024 * 1024)
        log_fn(f"  ✅ Final video: {final_path} ({size_mb:.0f}MB)")
        return str(final_path)

    log_fn("  ❌ Final composite failed")
    return None
