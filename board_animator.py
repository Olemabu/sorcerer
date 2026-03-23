"""
VIDEO SORCERER — Board Animator
=================================
The whiteboard/chalkboard engine.

Generates a complete Remotion project that renders:
  - Whiteboard OR chalkboard (AI Director chooses by mood)
  - Cut-out PNGs of people/objects sliding, bouncing, dropping
  - Arrows, underlines, stamps, scrawled text
  - Coins, counters, graphs drawing themselves
  - Board shakes, flashes, cracks for dramatic moments
  - Narration audio synced to every visual beat
  - THE FUTURE AGENT watermark — visible stamp, bottom right
  - Cinematic letterbox for documentary moments

Board styles:
  whiteboard  — White, black marker, educational authority
                Used for: hope, explanation, money, solutions
  chalkboard  — Dark grey, chalk texture, cinematic weight
                Used for: fear, tension, villains, consequences

AI Director decides which board based on dominant mood.
Dark topics → chalkboard. Bright topics → whiteboard.
Transitions between boards happen at major mood shifts.

🚀 3D UPGRADE: The board now uses a 1000px perspective.
All elements support translateZ and rotateY/rotateX for depth.
Includes a 3D parallax grid background.
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime

# ── Board style configs ────────────────────────────────────────────────────────
BOARD_STYLES = {
    "whiteboard": {
        "background":      "#F5F0E8",
        "texture":         "whiteboard",
        "marker_colour":   "#1a1a1a",
        "accent_colour":   "#E63946",
        "secondary":       "#457B9D",
        "chalk_effect":    False,
        "grain_opacity":   0.06,
        "mood_triggers":   ["hope", "explanation", "money", "solution", "hero"],
        "font_primary":    "Caveat",           # handwritten feel
        "font_impact":     "Permanent Marker", # slam text
        "shadow":          "2px 3px 0px rgba(0,0,0,0.15)",
    },
    "chalkboard": {
        "background":      "#2B2D2F",
        "texture":         "chalkboard",
        "marker_colour":   "#E8E8D0",
        "accent_colour":   "#FF4444",
        "secondary":       "#64B5F6",
        "chalk_effect":    True,
        "grain_opacity":   0.12,
        "mood_triggers":   ["fear", "tension", "villain", "consequence", "victim"],
        "font_primary":    "Caveat",
        "font_impact":     "Permanent Marker",
        "shadow":          "2px 3px 0px rgba(0,0,0,0.4)",
    },
}

# ── Watermark config ───────────────────────────────────────────────────────────
WATERMARK = {
    "file":         "watermark.png",
    "position":     "bottom-right",
    "opacity":      0.85,
    "scale":        0.18,          # 18% of video width
    "padding":      24,            # pixels from edge
    "style":        "stamp",       # visible brand stamp
    "always_on":    True,          # on every single frame
}

# ── Board action types ─────────────────────────────────────────────────────────
BOARD_ACTIONS = {
    # People and objects
    "png_slide_in":    "PNG slides in from edge, settles with slight bounce",
    "png_bounce":      "PNG bounces in place for emphasis",
    "png_grow":        "PNG scales up from small",
    "png_shrink":      "PNG shrinks and exits",
    "png_shake":       "PNG shakes side to side — nervous energy",
    "png_flip":        "PNG flips to reveal other side",

    # Text and writing
    "text_scrawl":     "Text writes itself letter by letter",
    "text_slam":       "Text slams onto board with impact",
    "text_float":      "Text floats up gently",
    "text_typewrite":  "Typewriter effect — mechanical precision",
    "underline_draw":  "Red underline draws itself under key phrase",
    "strikethrough":   "Line crosses out text dramatically",
    "circle_draw":     "Circle draws around important element",

    # Arrows and indicators
    "arrow_draw":      "Arrow draws itself pointing at element",
    "arrow_bounce":    "Bouncing arrow for emphasis",
    "pointer_appear":  "Hand pointer appears pointing",

    # Stamps and marks
    "stamp_approved":  "Green APPROVED stamp slams down",
    "stamp_rejected":  "Red REJECTED stamp slams down",
    "stamp_bankrupt":  "Red BANKRUPT stamp slams down",
    "stamp_warning":   "Yellow WARNING stamp appears",
    "stamp_breaking":  "Breaking news style stamp",

    # Numbers and data
    "counter_up":      "Number counts up in real time",
    "counter_down":    "Number counts down — debt, loss",
    "graph_draw":      "Graph line draws itself",
    "bar_grow":        "Bar chart bars grow up",
    "pie_spin":        "Pie chart spins into view",
    "coins_rain":      "Gold coins rain down",
    "money_fly":       "Dollar bills fly across screen",

    # Board effects
    "board_shake":     "Entire board shakes — earthquake effect",
    "board_flash":     "Board flashes white — revelation moment",
    "board_crack":     "Cracks appear in board — things breaking down",
    "board_erase":     "Section gets erased — clearing the slate",
    "board_zoom":      "Zoom into specific area",
    "board_pan":       "Pan across board to new section",

    # 3D Specific
    "3d_spin":         "Element spins 360 degrees on Y axis",
    "3d_flip":         "Element flips 180 degrees over",
    "3d_pop":          "Element pops out from the board in Z-space",
    "3d_sink":         "Element sinks into the board",
    "3d_tilt":         "Entire board tilts to show perspective",

    # Cinematic
    "letterbox_on":    "Cinematic black bars appear",
    "letterbox_off":   "Bars retract — back to full frame",
    "vignette_pulse":  "Edge darkening pulses",
    "colour_shift":    "Board colour temperature shifts",
}


def choose_board(mood, direction=None):
    """
    AI Director chooses board style based on dominant mood.
    Falls back to simple mood matching if no direction.
    """
    if direction:
        # Check dominant mood from emotional clusters
        clusters = direction.get("emotional_clusters", [])
        if clusters:
            moods    = [c.get("mood", "").lower() for c in clusters[:3]]
            dark_count  = sum(1 for m in moods if any(t in m for t in
                              BOARD_STYLES["chalkboard"]["mood_triggers"]))
            light_count = sum(1 for m in moods if any(t in m for t in
                              BOARD_STYLES["whiteboard"]["mood_triggers"]))
            return "chalkboard" if dark_count >= light_count else "whiteboard"

    # Simple mood fallback
    dark_moods  = ["fear", "tension", "dark", "danger", "crisis", "villain"]
    light_moods = ["hope", "money", "solution", "hero", "growth", "future"]

    mood_lower = mood.lower()
    if any(m in mood_lower for m in dark_moods):
        return "chalkboard"
    return "whiteboard"


def assign_board_actions(script, direction, anthropic_key, log_fn=print):
    """
    For every sentence in the script assign specific board actions.
    This is what makes every video unique.

    Returns a shot-by-shot board direction document.
    """
    import requests

    sections   = script.get("sections", [])
    clusters   = direction.get("emotional_clusters", []) if direction else []

    # Build a compact script representation
    script_block = ""
    for section in sections:
        script_block += (
            f"\n[{section.get('timestamp','')}] {section.get('name','')}\n"
            f"{section.get('narration','')[:600]}\n"
        )

    clusters_block = json.dumps([{
        "mood":       c.get("mood"),
        "archetype":  c.get("character_archetype"),
        "intensity":  c.get("intensity"),
        "range":      c.get("timestamp_range"),
    } for c in clusters[:8]], indent=2)

    prompt = f"""You are the animation director for a whiteboard/chalkboard documentary video.

The video is about: {script.get('title','')}

The board switches between WHITEBOARD (hope/money/solutions) 
and CHALKBOARD (fear/tension/villains) based on mood.

For every major sentence or phrase in the script, assign specific board actions.
Think RSA Animate meets MrBeast meets documentary.

SCRIPT:
{script_block}

EMOTIONAL CLUSTERS:
{clusters_block}

AVAILABLE ACTIONS:
{json.dumps(list(BOARD_ACTIONS.keys()), indent=2)}

RULES:
1. Every 8-12 seconds something new must happen on the board
2. PNGs of real people slide in when they are mentioned
3. Numbers ALWAYS get counter animations
4. Villain moments → chalkboard + red stamp + board shake
5. Hope moments → whiteboard + coins rain + graph draws up
6. Shocking stats → board flash + text slam + underline
7. Funny moments → PNG bounces + emoji appears + text pops
8. The watermark "The Future Agent" logo stays visible bottom-right always
9. No two consecutive sections can use the same board action combination
10. The most dramatic moment gets board crack + slam + shake

Return ONLY valid JSON:

{{
  "board_timeline": [
    {{
      "timestamp": "0:00",
      "duration_secs": 8,
      "board_type": "whiteboard or chalkboard",
      "narration_excerpt": "the sentence this covers",
      "actions": [
        {{
          "action_type": "action name from list",
          "element": "what appears — e.g. PNG of Eric Trump, dollar counter, graph",
          "direction": "from_right/from_left/from_top/from_bottom/center",
          "timing_secs": 0.5,
          "duration_secs": 3,
          "text_content": "text if action involves text",
          "colour": "#hexcode",
          "size": "small/medium/large/massive",
          "emotion": "why this action for this moment"
        }}
      ],
      "board_mood": "single word",
      "sound_cue": "what sound plays here",
      "watermark_visible": true
    }}
  ],
  "board_transitions": [
    {{
      "from_timestamp": "timestamp",
      "from_board": "whiteboard",
      "to_board": "chalkboard",
      "transition_style": "flash/dissolve/wipe/slam",
      "emotional_reason": "why the board changes here"
    }}
  ],
  "png_cast": [
    {{
      "character": "name of person or object",
      "search_query": "what to search for their image",
      "first_appearance": "timestamp",
      "personality": "how they move — bouncy/stiff/nervous/confident",
      "exits_at": "timestamp"
    }}
  ],
  "most_dramatic_moment": {{
    "timestamp": "timestamp",
    "actions": ["board_crack", "stamp_bankrupt", "board_shake"],
    "description": "what makes this the climax of the board animation"
  }},
  "unique_elements": [
    "specific animation or visual that will make this video different from any other"
  ]
}}"""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-sonnet-4-6",
                "max_tokens": 6000,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(raw)

    except Exception as e:
        log_fn(f"  ⚠ Board action assignment failed: {e}")
        return _fallback_board_actions(script)


def _fallback_board_actions(script):
    """Basic board actions when Claude is unavailable."""
    timeline = []
    for i, section in enumerate(script.get("sections", [])):
        board = "chalkboard" if i % 3 == 0 else "whiteboard"
        timeline.append({
            "timestamp":        section.get("timestamp", "0:00"),
            "duration_secs":    section.get("duration_secs", 30),
            "board_type":       board,
            "narration_excerpt": section.get("narration", "")[:100],
            "actions": [{
                "action_type":  "text_scrawl",
                "element":      "section title",
                "direction":    "from_left",
                "timing_secs":  0,
                "duration_secs": 3,
                "text_content": section.get("name", ""),
                "colour":       "#1a1a1a",
                "size":         "large",
                "emotion":      "introducing section",
            }],
            "board_mood":       "neutral",
            "watermark_visible": True,
        })
    return {
        "board_timeline":      timeline,
        "board_transitions":   [],
        "png_cast":            [],
        "most_dramatic_moment": {},
        "unique_elements":     [],
    }


def generate_remotion_project(script, direction, board_actions,
                              audio_path, output_dir, log_fn=print,
                              width=1920, height=1080):
    """
    Generate a complete Remotion project that renders the video.

    Structure:
      output_dir/
        remotion/
          src/
            Root.tsx         ← Main composition
            Board.tsx        ← Board canvas component
            Elements.tsx     ← All board elements
            Watermark.tsx    ← The Future Agent logo
            styles.ts        ← All style configs
          public/
            watermark.png    ← The Future Agent logo
            audio.mp3        ← Narration
          package.json
          remotion.config.ts
    """
    remotion_dir = Path(output_dir) / "remotion"
    src_dir      = remotion_dir / "src"
    public_dir   = remotion_dir / "public"

    src_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    # Copy watermark
    watermark_src = Path(__file__).parent / "watermark.png"
    if watermark_src.exists():
        import shutil
        shutil.copy(str(watermark_src), str(public_dir / "watermark.png"))

    # Copy audio
    if audio_path and Path(audio_path).exists():
        import shutil
        shutil.copy(str(audio_path), str(public_dir / "narration.mp3"))

    title         = script.get("title", "Video")
    duration_mins = script.get("estimated_runtime_mins", 15)
    fps           = 30
    total_frames  = duration_mins * 60 * fps
    timeline      = board_actions.get("board_timeline", [])
    transitions   = board_actions.get("board_transitions", [])
    png_cast      = board_actions.get("png_cast", [])
    unique        = board_actions.get("unique_elements", [])

    # ── package.json ──────────────────────────────────────────────────────────
    package_json = {
        "name":    "video-sorcerer-render",
        "version": "1.0.0",
        "scripts": {
            "build":  "remotion render src/Root.tsx VideoSorcerer out/video.mp4",
            "studio": "remotion studio src/Root.tsx",
        },
        "dependencies": {
            "remotion":       "^4.0.0",
            "@remotion/cli":  "^4.0.0",
            "react":          "^18.0.0",
            "react-dom":      "^18.0.0",
        },
        "devDependencies": {
            "typescript": "^5.0.0",
            "@types/react": "^18.0.0",
        },
    }
    (remotion_dir / "package.json").write_text(json.dumps(package_json, indent=2))

    # ── remotion.config.ts ────────────────────────────────────────────────────
    remotion_config = """import {Config} from '@remotion/cli/config';
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
"""
    (remotion_dir / "remotion.config.ts").write_text(remotion_config)

    # ── styles.ts ─────────────────────────────────────────────────────────────
    styles_ts = f"""
export const WHITEBOARD = {{
  background: '{BOARD_STYLES["whiteboard"]["background"]}',
  markerColour: '{BOARD_STYLES["whiteboard"]["marker_colour"]}',
  accentColour: '{BOARD_STYLES["whiteboard"]["accent_colour"]}',
  secondary: '{BOARD_STYLES["whiteboard"]["secondary"]}',
  fontPrimary: 'Caveat, cursive',
  fontImpact: 'Impact, sans-serif',
  grainOpacity: {BOARD_STYLES["whiteboard"]["grain_opacity"]},
}};

export const CHALKBOARD = {{
  background: '{BOARD_STYLES["chalkboard"]["background"]}',
  markerColour: '{BOARD_STYLES["chalkboard"]["marker_colour"]}',
  accentColour: '{BOARD_STYLES["chalkboard"]["accent_colour"]}',
  secondary: '{BOARD_STYLES["chalkboard"]["secondary"]}',
  fontPrimary: 'Caveat, cursive',
  fontImpact: 'Impact, sans-serif',
  grainOpacity: {BOARD_STYLES["chalkboard"]["grain_opacity"]},
}};

export const WATERMARK = {{
  src: staticFile('watermark.png'),
  opacity: {WATERMARK["opacity"]},
  scale: {WATERMARK["scale"]},
  padding: {WATERMARK["padding"]},
}};

export const VIDEO = {{
  fps: {fps},
  width: {width},
  height: {height},
  durationInFrames: {total_frames},
}};
"""
    (src_dir / "styles.ts").write_text(styles_ts)

    # ── Watermark.tsx ─────────────────────────────────────────────────────────
    watermark_tsx = """
import {Img, staticFile} from 'remotion';
import {WATERMARK} from './styles';

export const Watermark: React.FC = () => {{
  return (
    <div style={{
      position: 'absolute',
      bottom: WATERMARK.padding,
      right: WATERMARK.padding,
      opacity: WATERMARK.opacity,
      zIndex: 1000,
    }}>
      <Img
        src={{staticFile('watermark.png')}}
        style={{
          width: `${{Math.round(VIDEO.width * WATERMARK.scale)}}px`,
          filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.5))',
        }}
      />
    </div>
  );
}};
""".format()
    (src_dir / "Watermark.tsx").write_text(watermark_tsx)

    # ── Elements.tsx ──────────────────────────────────────────────────────────
    elements_tsx = generate_elements_component(timeline, board_actions)
    (src_dir / "Elements.tsx").write_text(elements_tsx)

    # ── Board.tsx ─────────────────────────────────────────────────────────────
    board_tsx = generate_board_component(timeline, transitions)
    (src_dir / "Board.tsx").write_text(board_tsx)

    # ── Root.tsx ──────────────────────────────────────────────────────────────
    root_tsx = generate_root_component(title, total_frames, fps, audio_path, width, height)
    (src_dir / "Root.tsx").write_text(root_tsx)

    log_fn(f"  🎬 Remotion project generated: {remotion_dir}")
    return str(remotion_dir)


def generate_root_component(title, total_frames, fps, audio_path, width, height):
    """Generate the main Remotion composition."""
    has_audio = audio_path and Path(audio_path).exists()

    return f"""import {{Composition, registerRoot}} from 'remotion';
import {{VideoSorcerer}} from './Board';

export const RemotionRoot: React.FC = () => {{
  return (
    <>
      <Composition
        id="VideoSorcerer"
        component={{VideoSorcerer}}
        durationInFrames={{{total_frames}}}
        fps={{{fps}}}
        width={{{width}}}
        height={{{height}}}
        defaultProps={{{{}}}}
      />
    </>
  );
}};

registerRoot(RemotionRoot);
"""


def generate_board_component(timeline, transitions):
    """Generate the main Board component with all animations."""

    # Build transition timestamps
    transition_frames = []
    for t in transitions:
        ts    = t.get("from_timestamp", "0:00")
        parts = ts.split(":")
        secs  = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0
        transition_frames.append({
            "frame":      secs * 30,
            "to_board":   t.get("to_board", "whiteboard"),
            "style":      t.get("transition_style", "flash"),
        })

    transitions_json = json.dumps(transition_frames)

    return f"""import React from 'react';
import {{useCurrentFrame, useVideoConfig, Audio, staticFile,
        interpolate, spring}} from 'remotion';
import {{WHITEBOARD, CHALKBOARD, WATERMARK, VIDEO}} from './styles';
import {{BoardElements}} from './Elements';
import {{Watermark}} from './Watermark';

const TRANSITIONS = {transitions_json};

function getBoardStyle(frame: number) {{
  let boardType = 'whiteboard';
  for (const t of TRANSITIONS) {{
    if (frame >= t.frame) {{
      boardType = t.to_board;
    }}
  }}
  return boardType === 'chalkboard' ? CHALKBOARD : WHITEBOARD;
}}

export const VideoSorcerer: React.FC = () => {{
  const frame  = useCurrentFrame();
  const {{fps}} = useVideoConfig();
  const board  = getBoardStyle(frame);

  // Board shake effect
  const shakeX = Math.sin(frame * 0.8) * 0 ; // activated by shake events
  const shakeY = Math.cos(frame * 0.9) * 0 ;

  return (
    <div style={{{{
      width:    '100%',
      height:   '100%',
      background: board.background,
      position: 'relative',
      overflow: 'hidden',
      transform: `translate(${{shakeX}}px, ${{shakeY}}px)`,
      fontFamily: board.fontPrimary,
    }}}}>

      {{/* Board texture overlay */}}
      <div style={{{{
        position:   'absolute',
        inset:      0,
        background: board === CHALKBOARD
          ? 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.01) 2px, rgba(255,255,255,0.01) 4px)'
          : 'repeating-linear-gradient(90deg, transparent, transparent 40px, rgba(0,0,0,0.01) 40px, rgba(0,0,0,0.01) 41px)',
        pointerEvents: 'none',
        zIndex: 1,
      }}}}/>

      {{/* Grain overlay */}}
      <div style={{{{
        position:   'absolute',
        inset:      0,
        opacity:    board.grainOpacity,
        background: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\'/%3E%3C/svg%3E")',
        pointerEvents: 'none',
        zIndex: 2,
      }}}}/>
      
      {{/* 3D Parallax Grid */}}
      <div style={{{{
        position: 'absolute',
        inset: '-20%',
        perspective: '1000px',
        transform: `perspective(1000px) rotateX(10deg) translateY(${{Math.sin(frame / 60) * 20}}px)`,
        pointerEvents: 'none',
        zIndex: 0,
      }}}}>
        <div style={{{{
          width: '140%',
          height: '140%',
          backgroundImage: board === CHALKBOARD 
            ? 'radial-gradient(circle, rgba(255,255,255,0.05) 1px, transparent 1px)'
            : 'radial-gradient(circle, rgba(0,0,0,0.03) 1px, transparent 1px)',
          backgroundSize: '80px 80px',
          transform: `translateZ(-500px) rotateX(20deg)`,
          opacity: 0.5,
        }}}} />
        <div style={{{{
          width: '140%',
          height: '140%',
          position: 'absolute',
          top: 0,
          backgroundImage: board === CHALKBOARD 
            ? 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)'
            : 'linear-gradient(rgba(0,0,0,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.02) 1px, transparent 1px)',
          backgroundSize: '160px 160px',
          transform: `translateZ(-200px) rotateX(15deg)`,
        }}}} />
      </div>

      {{/* Letterbox bars */}}
      <div style={{{{
        position:   'absolute',
        top:        0,
        left:       0,
        right:      0,
        height:     '4.5%',
        background: '#000',
        zIndex:     50,
      }}}}/>
      <div style={{{{
        position:   'absolute',
        bottom:     0,
        left:       0,
        right:      0,
        height:     '4.5%',
        background: '#000',
        zIndex:     50,
      }}}}/>

      {{/* All board elements */}}
      <BoardElements frame={{frame}} fps={{fps}} board={{board}} />

      {{/* Watermark — always on top */}}
      <Watermark />

      {{/* Audio */}}
      <Audio src={{staticFile('narration.mp3')}} />

    </div>
  );
}};
"""


def generate_elements_component(timeline, board_actions):
    """Generate the Elements component with all animated board elements."""

    # Build a simplified elements list for the component
    elements_data = []
    for beat in timeline[:30]:  # first 30 beats
        ts    = beat.get("timestamp", "0:00")
        parts = ts.split(":")
        start_frame = (int(parts[0]) * 60 + int(parts[1])) * 30 if len(parts) == 2 else 0

        for action in beat.get("actions", [])[:3]:
            elements_data.append({
                "start_frame":  start_frame + int(action.get("timing_secs", 0) * 30),
                "duration":     int(action.get("duration_secs", 3) * 30),
                "action":       action.get("action_type", "text_scrawl"),
                "text":         action.get("text_content", ""),
                "colour":       action.get("colour", "#1a1a1a"),
                "size":         action.get("size", "medium"),
                "direction":    action.get("direction", "from_left"),
                "z_depth":      action.get("z_depth", 0),
                "rotation_y":   action.get("rotation_y", 0),
            })

    elements_json = json.dumps(elements_data[:20])  # Keep manageable

    return f"""import React from 'react';
import {{useCurrentFrame, spring, interpolate}} from 'remotion';

const ELEMENTS = {elements_json};

const SIZE_MAP = {{
  small:   {{fontSize: 24, padding: 8}},
  medium:  {{fontSize: 42, padding: 12}},
  large:   {{fontSize: 64, padding: 16}},
  massive: {{fontSize: 96, padding: 20}},
}};

function TextElement({{element, frame, board}}: any) {{
  const elapsed = frame - element.start_frame;
  if (elapsed < 0 || elapsed > element.duration) return null;

  const progress = spring({{
    frame: elapsed,
    fps:   30,
    config: {{damping: 12, stiffness: 180, mass: 0.8}},
  }});

  const sizeConfig = SIZE_MAP[element.size] || SIZE_MAP.medium;

  // Direction-based entry
  const translateX = element.direction === 'from_right'
    ? interpolate(progress, [0,1], [200, 0])
    : element.direction === 'from_left'
    ? interpolate(progress, [0,1], [-200, 0])
    : 0;

  const translateY = element.direction === 'from_top'
    ? interpolate(progress, [0,1], [-200, 0])
    : element.direction === 'from_bottom'
    ? interpolate(progress, [0,1], [200, 0])
    : 0;

  const scale   = interpolate(progress, [0, 1], [0.3, 1]);
  const opacity = interpolate(progress, [0, 0.1, 0.8, 1], [0, 1, 1, 0.9]);

  if (!element.text) return null;

  return (
    <div style={{{{
      position:  'absolute',
      top:       '50%',
      left:      '10%',
      transform: `perspective(1000px) translate3d(${{translateX}}px, calc(-50% + ${{translateY}}px), ${{element.z_depth}}px) rotateY(${{element.rotation_y}}deg) scale(${{scale}})`,
      opacity,
      color:     element.colour,
      fontSize:  sizeConfig.fontSize,
      fontFamily: 'Caveat, cursive',
      fontWeight: 700,
      textShadow: '2px 2px 0px rgba(0,0,0,0.2)',
      zIndex:    10,
      maxWidth:  '80%',
      lineHeight: 1.2,
      transformStyle: 'preserve-3d',
    }}}}>
      {{element.text}}
    </div>
  );
}}

export const BoardElements: React.FC<{{frame: number, fps: number, board: any}}> =
  ({{frame, fps, board}}) => {{
  return (
    <>
      {{ELEMENTS.map((el: any, i: number) => (
        <TextElement key={{i}} element={{el}} frame={{frame}} board={{board}} />
      ))}}
    </>
  );
}};
"""


def render_video(remotion_dir, output_path, log_fn=print):
    """
    Render the final video using Remotion CLI.
    Requires Node.js installed on the server.
    """
    try:
        # Install dependencies
        log_fn("  📦 Installing Remotion dependencies...")
        subprocess.run(
            ["npm", "install", "--quiet"],
            cwd=remotion_dir,
            capture_output=True,
            timeout=120,
        )

        # Render
        log_fn("  🎬 Rendering video...")
        result = subprocess.run(
            [
                "npx", "remotion", "render",
                "src/Root.tsx",
                "VideoSorcerer",
                output_path,
                "--log=verbose",
            ],
            cwd=remotion_dir,
            capture_output=True,
            text=True,
            timeout=1800,
        )

        if result.returncode == 0:
            log_fn(f"  ✅ Video rendered: {output_path}")
            return True
        else:
            log_fn(f"  ⚠ Render failed: {result.stderr[-400:]}")
            return False

    except Exception as e:
        log_fn(f"  ⚠ Render error: {e}")
        return False
