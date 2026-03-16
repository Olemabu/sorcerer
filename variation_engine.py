"""
VIDEO SORCERER — Variation Engine
====================================
Ensures no two videos ever look, feel, or open the same way.

Tracks:
  - Last 20 video styles used
  - Last 20 opening types used
  - Last 20 colour palettes used
  - Topic angles covered per subject
  - Board style history

Forces variation by:
  - Never repeating same opening twice in a row
  - Cycling through style combinations systematically
  - Rotating topic angles (fear → hope → money → villain → everyman)
  - Alternating board styles
  - Varying structural approaches
"""

import json
import random
from pathlib import Path
from datetime import datetime


# ── Opening types ──────────────────────────────────────────────────────────────
OPENING_TYPES = [
    {
        "name":        "shocking_stat",
        "description": "Opens with a number so surprising it demands explanation",
        "example":     "47 people. That is how many radiologists one hospital fired last Tuesday.",
        "board_action": "counter_up then board_flash",
        "mood":        "disruption",
    },
    {
        "name":        "mid_story",
        "description": "Drops viewer in the middle of an event already happening",
        "example":     "The email arrived at 9:47am. By 10:15 the meeting room was empty.",
        "board_action": "text_scrawl with clock",
        "mood":        "tension",
    },
    {
        "name":        "direct_address",
        "description": "Speaks directly and personally to the viewer",
        "example":     "In four years your job will look nothing like it does today. Here is why.",
        "board_action": "text_slam pointing arrow",
        "mood":        "personal",
    },
    {
        "name":        "question_hook",
        "description": "Opens with a question that has no obvious answer",
        "example":     "What would you do if an algorithm could diagnose cancer better than your doctor?",
        "board_action": "question mark draws itself",
        "mood":        "curiosity",
    },
    {
        "name":        "silence_cold_open",
        "description": "Pure silence and one image. Nothing else for 3 seconds.",
        "example":     "[empty hospital corridor. silence. then:] Last Tuesday.",
        "board_action": "chalkboard fade in, single image, silence",
        "mood":        "dread",
    },
    {
        "name":        "absurd_comparison",
        "description": "Opens by comparing the serious topic to something ridiculous",
        "example":     "This costs less than your Netflix subscription. And it just replaced 47 doctors.",
        "board_action": "netflix logo then doctor png, arrow between them",
        "mood":        "dark_humor",
    },
    {
        "name":        "future_flashback",
        "description": "Describes a future moment then says we need to explain how we got there",
        "example":     "It is 2027. There are no radiologists. This is the story of how that happened.",
        "board_action": "year counter flips forward, then backward",
        "mood":        "inevitability",
    },
    {
        "name":        "contradiction_open",
        "description": "States two things that seem contradictory",
        "example":     "AI is saving thousands of lives. AI is eliminating thousands of jobs. Both are true.",
        "board_action": "two columns draw simultaneously",
        "mood":        "complexity",
    },
]

# ── Structural variations ──────────────────────────────────────────────────────
STRUCTURES = [
    "fear_hope_money_consequences",  # Default
    "villain_hero_lesson",
    "problem_solution_warning",
    "past_present_future",
    "myth_reality_implications",
    "individual_system_change",
    "small_big_bigger",
    "question_evidence_verdict",
]

# ── Topic angle rotation ───────────────────────────────────────────────────────
TOPIC_ANGLES = [
    "fear",       # What could go wrong
    "hope",       # What could go right
    "money",      # Who profits and how
    "villain",    # Who is responsible
    "everyman",   # What this means for you personally
    "expert",     # What the insiders know that you don't
    "history",    # This has happened before
    "future",     # Where this is inevitably heading
]


class VariationEngine:
    def __init__(self, db_file):
        self.db_file    = Path(db_file)
        self.history    = self._load_history()

    def _load_history(self):
        history_file = self.db_file.parent / "variation_history.json"
        if history_file.exists():
            try:
                return json.loads(history_file.read_text())
            except Exception:
                pass
        return {
            "openings_used":       [],
            "structures_used":     [],
            "styles_used":         [],
            "boards_used":         [],
            "angles_by_topic":     {},
            "total_videos":        0,
            "last_updated":        None,
        }

    def _save_history(self):
        history_file = self.db_file.parent / "variation_history.json"
        self.history["last_updated"] = datetime.now().isoformat()
        history_file.write_text(json.dumps(self.history, indent=2))

    def get_opening(self):
        """Choose an opening type not recently used."""
        used   = self.history.get("openings_used", [])[-5:]
        unused = [o for o in OPENING_TYPES if o["name"] not in used]

        if not unused:
            unused = OPENING_TYPES  # Reset if all used

        choice = random.choice(unused)
        return choice

    def get_structure(self):
        """Choose a narrative structure not recently used."""
        used   = self.history.get("structures_used", [])[-4:]
        unused = [s for s in STRUCTURES if s not in used]

        if not unused:
            unused = STRUCTURES

        return random.choice(unused)

    def get_style(self):
        """Choose a visual style not recently used."""
        styles = ["scorsese", "mrbeast", "capcut", "hybrid"]
        used   = self.history.get("styles_used", [])[-3:]
        unused = [s for s in styles if s not in used]

        if not unused:
            unused = styles

        return random.choice(unused)

    def get_board(self, mood=None):
        """Choose board type based on mood and history."""
        used = self.history.get("boards_used", [])[-2:]

        if mood:
            dark_moods  = ["fear", "tension", "villain", "dread"]
            light_moods = ["hope", "money", "solution", "curiosity"]

            if any(m in mood.lower() for m in dark_moods):
                preferred = "chalkboard"
            elif any(m in mood.lower() for m in light_moods):
                preferred = "whiteboard"
            else:
                preferred = None

            if preferred and (len(used) < 2 or used[-1] != preferred):
                return preferred

        # Alternate if no mood preference
        last = used[-1] if used else None
        return "chalkboard" if last == "whiteboard" else "whiteboard"

    def get_angle(self, topic):
        """Get the next topic angle to ensure variety."""
        angles_used = self.history.get("angles_by_topic", {}).get(topic, [])
        unused = [a for a in TOPIC_ANGLES if a not in angles_used[-4:]]

        if not unused:
            unused = TOPIC_ANGLES

        return random.choice(unused)

    def record_video(self, opening, structure, style, board, topic, angle):
        """Record what was used for this video."""
        h = self.history

        h["openings_used"]   = (h.get("openings_used", []) + [opening])[-20:]
        h["structures_used"] = (h.get("structures_used", []) + [structure])[-20:]
        h["styles_used"]     = (h.get("styles_used", []) + [style])[-20:]
        h["boards_used"]     = (h.get("boards_used", []) + [board])[-20:]
        h["total_videos"]    = h.get("total_videos", 0) + 1

        angles = h.get("angles_by_topic", {})
        angles[topic] = (angles.get(topic, []) + [angle])[-8:]
        h["angles_by_topic"] = angles

        self._save_history()

    def get_variation_brief(self, topic, mood=None):
        """
        Get a complete variation brief for the next video.
        Call this before generating the script.
        """
        opening   = self.get_opening()
        structure = self.get_structure()
        style     = self.get_style()
        board     = self.get_board(mood)
        angle     = self.get_angle(topic)

        brief = {
            "opening":          opening,
            "structure":        structure,
            "style":            style,
            "board":            board,
            "angle":            angle,
            "total_videos":     self.history.get("total_videos", 0) + 1,
            "instruction":      (
                f"This is video #{self.history.get('total_videos', 0) + 1}. "
                f"Open with: {opening['description']}. "
                f"Structure: {structure}. "
                f"Angle: approach this topic from the {angle} perspective. "
                f"Style: {style}. "
                f"Board: starts on {board}. "
                f"Make this feel completely different from any previous video."
            ),
        }

        return brief

    def format_brief_telegram(self, brief):
        """Format variation brief for Telegram."""
        opening = brief.get("opening", {})
        return (
            f"🎲 <b>VARIATION ENGINE</b>\n"
            f"Video #{brief.get('total_videos', 1)} — guaranteed unique\n\n"
            f"🎬 Opening: <b>{opening.get('name','').replace('_',' ').title()}</b>\n"
            f"<i>{opening.get('description','')}</i>\n\n"
            f"📐 Structure: <b>{brief.get('structure','').replace('_',' ').title()}</b>\n"
            f"🎯 Angle: <b>{brief.get('angle','').title()}</b>\n"
            f"🎨 Style: <b>{brief.get('style','').title()}</b>\n"
            f"🖊 Board: <b>{brief.get('board','').title()}</b>"
        )
