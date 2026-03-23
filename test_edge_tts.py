import os
import sys
import traceback
import locale

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from narrator import narrate_full_script

load_dotenv()

voice_id = os.environ.get("EDGE_TTS_VOICE", "en-US-ChristopherNeural")

script = {
    "sections": [{"name": "Intro", "timestamp": "0_00", "narration": "Hello."}],
    "cta_narration": "Bye."
}

output_dir = "./test_edge_tts_output"
os.makedirs(output_dir, exist_ok=True)

try:
    results = narrate_full_script(script, voice_id, output_dir, print)
    print(f"RESULTS: {results}")
    if results and results.get("master_audio"):
        print(f"SUCCESS: {results['master_audio']}")
    else:
        print("FAIL: master_audio is None")
except Exception as e:
    print("EXCEPTION:", e)
    traceback.print_exc()
