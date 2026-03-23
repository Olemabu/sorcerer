import os
from dotenv import load_dotenv
from soundtrack import generate_soundtrack

load_dotenv()

freesound_key = os.environ.get("FREESOUND_API_KEY")

if not freesound_key:
    print("FREESOUND_API_KEY not found in .env")
    exit(1)

style = {
    "music": {
        "mood": "cinematic tension",
        "style": "dark ambient"
    }
}

output_dir = "./test_freesound_output"
os.makedirs(output_dir, exist_ok=True)

print("Starting test...")
soundtrack_path = generate_soundtrack(
    style=style,
    video_duration_secs=60,
    anthropic_key="",
    freesound_key=freesound_key,
    output_dir=output_dir,
    log_fn=print
)

if soundtrack_path:
    print(f"SUCCESS! Downloaded to: {soundtrack_path}")
else:
    print("FAILED to download soundtrack.")
