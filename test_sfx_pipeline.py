import os
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from soundtrack import download_sfx_moments
from compositor import composite_full_video

load_dotenv()

freesound_key = os.environ.get("FREESOUND_API_KEY")
# Use absolute path for output_dir
output_dir = Path(os.getcwd()).absolute() / "test_sfx_output"

if output_dir.exists():
    shutil.rmtree(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)

print(f"Output directory: {output_dir}")

# 1. Mock SFX moments from AI Director
sfx_moments = [
    {"timestamp": "0:02", "search_keyword": "cinematic boom", "sound": "Boom"},
    {"timestamp": "0:04", "search_keyword": "lightning bolt", "sound": "Thunder"}
]

print("\n--- Step 1: Testing SFX Downloading ---")
sfx_data = download_sfx_moments(sfx_moments, freesound_key, str(output_dir), log_fn=print)

if len(sfx_data) == len(sfx_moments):
    print("✅ SFX Download Success!")
else:
    print(f"⚠️ Only downloaded {len(sfx_data)}/{len(sfx_moments)} SFX.")

for s in sfx_data:
    print(f"  - {s['sound']} at {s['timestamp']}: {s['path']}")
    # Verify file existence
    if Path(s['path']).exists():
        print(f"    ✓ File exists (size: {Path(s['path']).stat().st_size} bytes)")
    else:
        print(f"    ❌ FILE DOES NOT EXIST")

# 2. Mock data for compositor
print("\n--- Step 2: Testing SFX Mixing ---")

# Create a dummy naration audio file
dummy_audio = output_dir / "narration_dummy.mp3"
print(f"Creating dummy audio: {dummy_audio}")
subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '10', '-q:a', '9', '-acodec', 'libmp3lame', str(dummy_audio)], capture_output=True)

narration_data = {
    "sections": [
        {"name": "intro", "audio_file": str(dummy_audio), "duration_secs": 10}
    ],
    "total_duration_secs": 10
}

# Create a dummy video file
dummy_video_file = output_dir / "video_dummy.mp4"
print(f"Creating dummy video: {dummy_video_file}")
subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=1280x720:r=25', '-t', '10', str(dummy_video_file)], capture_output=True)

# Mock footage map
footage_map = [
    {
        "section_name": "intro",
        "clips": [{"file": str(dummy_video_file), "duration": 10}],
        "title_cards": [],
        "lower_thirds": [],
        "duration_secs": 10
    }
]

style = {
    "music": {"duck_level_db": -18},
    "effects": {"film_grain": False, "vignette": False, "letterbox": False, "slow_zoom_broll": False}
}

# Now run compositor
try:
    final_video = composite_full_video(
        narration_data,
        footage_map,
        soundtrack_path=None, 
        style=style,
        output_dir=str(output_dir),
        sfx_data=sfx_data,
        log_fn=print
    )

    if final_video and Path(final_video).exists():
        print(f"✅ Final video with SFX created: {final_video}")
        duration = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', final_video], capture_output=True, text=True).stdout.strip()
        print(f"   Duration: {duration}s")
    else:
        print("❌ Failed to create final video.")
except Exception as e:
    print(f"❌ Compositor error: {e}")

print("\nTest Complete.")
