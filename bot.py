"""
SORCERER — Telegram Bot Controller
====================================
Control everything from your Telegram chat.
No terminal. No Railway. Just chat with your bot.

Commands:
  /add @channel     — Add a channel to the radar
  /remove channel   — Stop watching a channel
  /list             — See all channels being watched
  /scan             — Run a scan right now
  /status           — How is SORCERER doing
  /watch keyword    — Add a Google Trends keyword to monitor
  /trends           — See all trend keywords being watched
  /help             — Show all commands
"""

import os
import json
import time
import threading
import requests
from datetime import datetime
from pathlib import Path


TG_API = "https://api.telegram.org"


class SorcererBot:
    def __init__(self, token, chat_id, db_file, log_fn=print):
        self.token    = token
        self.chat_id  = str(chat_id)
        self.db_file  = db_file
        self.log_fn   = log_fn
        self.offset   = 0
        self.running  = False
        self.scan_fn  = None
        self.add_fn   = None
        self.abort_flag = False

    def send(self, text, chat_id=None):
        if not self.token:
            return
        try:
            requests.post(
                f"{TG_API}/bot{self.token}/sendMessage",
                json={
                    "chat_id":    chat_id or self.chat_id,
                    "text":       text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
        except Exception as e:
            self.log_fn(f"  ⚠ Telegram send error: {e}")

    def get_updates(self):
        try:
            r = requests.get(
                f"{TG_API}/bot{self.token}/getUpdates",
                params={"offset": self.offset, "timeout": 30, "limit": 10},
                timeout=35,
            )
            r.raise_for_status()
            return r.json().get("result", [])
        except Exception:
            return []

    def load_db(self):
        if Path(self.db_file).exists():
            return json.loads(Path(self.db_file).read_text())
        return {"channels": {}, "scans": 0, "total_alerts": 0, "last_scan": None}

    def handle_start(self, chat_id):
        self.send(
            "🧙 <b>SORCERER is awake.</b>\n\n"
            "I watch YouTube channels 24/7 and alert you the moment something goes viral.\n"
            "I also monitor Google Trends 24-48h before topics hit YouTube.\n\n"
            "Send /help to see what I can do.",
            chat_id
        )

    def handle_help(self, chat_id):
        self.send(
            "🧙 <b>SORCERER Commands</b>\n\n"
            "<b>Quick Setup (recommended)</b>\n"
            "/setup — Load preset channels for your niche\n"
            "/full — Load ALL channels (AI + Healthcare + Innovation)\n\n"
            "<b>YouTube Radar</b>\n"
            "/add @channel — Add a channel to watch\n"
            "/remove name — Stop watching a channel\n"
            "/list — See all channels being watched\n"
            "/scan — Run a scan right now\n\n"
            "<b>Google Trends</b>\n"
            "/watch keyword — Monitor a topic on Google Trends\n"
            "/trends — See all trend keywords\n\n"
            "<b>🧪 Concept Lab</b>\n"
            "/concept — Generate 5 wild viral series ideas\n"
            "/concept [niche] — Steer ideas (e.g. /concept tech)\n"
            "/concept pick [#] — Full series bible for idea #\n"
            "/conceive [#] — Produce a pilot episode now\n\n"
            "<b>✂️ Clipper</b>\n"
            "/clip [URL] — Download + AI-clip any YouTube video\n\n"
            "<b>🎬 Producer</b>\n"
            "/produce [URL or topic] — Full production package\n\n"
            "<b>Info</b>\n"
            "/status — How SORCERER is doing\n"
            "/usage — Token usage and cost report\n\n"
            "<b>AI Director</b>\n"
            "/direct — Direct your last script\n"
            "/scorsese /mrbeast /capcut /hybrid\n\n"
            "<b>Review & Publish</b>\n"
            "/approve — Upload video to all platforms\n"
            "/revise [notes] — Change something\n"
            "/restyle [style] — New visual style\n"
            "/preview_script — Read the full script\n"
            "/discard — Scrap this video\n\n"
            "<b>✍️ Script Directing</b>\n"
            "/script [TEXT] — Produce a video from a verbatim script\n\n"
            "/help — Show this message",
            chat_id
        )

    def handle_list(self, chat_id):
        db = self.load_db()
        channels = db.get("channels", {})
        if not channels:
            self.send(
                "📡 No channels added yet.\n\nUse /add @channel to start watching someone.",
                chat_id
            )
            return
        lines = [f"📡 <b>Watching {len(channels)} channel(s):</b>\n"]
        for i, ch in enumerate(channels.values(), 1):
            bl   = ch.get("baseline")
            base = f"{bl['median_vph']:,.0f} views/hr baseline" if bl else "building baseline..."
            lines.append(f"{i}. <b>{ch['title']}</b>\n   {ch.get('subscribers',0):,} subs · {base}")
        self.send("\n".join(lines), chat_id)

    def handle_add(self, chat_id, args):
        if not args:
            self.send("Please tell me which channel to add.\nExample: /add @mkbhd", chat_id)
            return
        channel = " ".join(args)
        self.send(f"🔍 Looking up <b>{channel}</b>...", chat_id)
        if self.add_fn:
            result = self.add_fn(channel)
            self.send(result, chat_id)
        else:
            self.send("⚠ Add function not available right now.", chat_id)

    def handle_remove(self, chat_id, args):
        if not args:
            self.send("Please tell me which channel to remove.\nExample: /remove mkbhd", chat_id)
            return
        query = " ".join(args).lower().lstrip("@")
        db    = self.load_db()
        match = next(
            (cid for cid, ch in db.get("channels", {}).items()
             if query in ch["title"].lower() or query == cid),
            None
        )
        if not match:
            self.send(f"❌ Channel not found: {query}\n\nUse /list to see what I'm watching.", chat_id)
            return
        title = db["channels"][match]["title"]
        del db["channels"][match]
        Path(self.db_file).write_text(json.dumps(db, indent=2))
        self.send(f"✅ Removed <b>{title}</b> from radar.", chat_id)

    def handle_scan(self, chat_id):
        self.send("⚡ Starting scan now...", chat_id)
        if self.scan_fn:
            threading.Thread(target=self._run_scan, args=(chat_id,), daemon=True).start()
        else:
            self.send("⚠ Scan function not available right now.", chat_id)

    def _run_scan(self, chat_id):
        try:
            db = self.load_db()
            channels = db.get("channels", {})

            if not channels:
                self.send(
                    "No channels on radar yet.\n\n"
                    "Use /add @channel or /setup to load a niche preset first.",
                    chat_id
                )
                return

            no_baseline = [ch["title"] for ch in channels.values() if not ch.get("baseline")]

            results = self.scan_fn()

            if results and results > 0:
                self.send(f"Scan complete -- {results} new signal(s) detected! Check above.", chat_id)
            elif no_baseline:
                names = "\n".join(f"  - {t}" for t in no_baseline[:8])
                extra = "\n  ..." if len(no_baseline) > 8 else ""
                self.send(
                    f"Scan complete -- {len(no_baseline)} channel(s) still building baseline\n"
                    "(need 3+ videos older than 48h).\n"
                    + names + extra +
                    "\n\nSignals will fire once baselines are ready. Run /scan again soon.",
                    chat_id
                )
            else:
                self.send(
                    "Scan complete -- no new signals right now.\n\n"
                    "All channels are below thresholds. "
                    "You will be alerted the moment something spikes.",
                    chat_id
                )
        except Exception as e:
            self.send(f"Scan error: {e}", chat_id)
    def handle_watch(self, chat_id, args):
        if not args:
            self.send(
                "Tell me what keyword to watch on Google Trends.\n\n"
                "Example: /watch AI agents\n"
                "Example: /watch autonomous AI\n\n"
                "I'll alert you 24-48h before this topic hits YouTube.",
                chat_id
            )
            return
        keyword = " ".join(args).lower().strip()
        try:
            from trends import add_manual_keywords
            keywords = add_manual_keywords(self.db_file, [keyword])
            self.send(
                f"📈 Now watching on Google Trends: <b>{keyword}</b>\n\n"
                f"Total trend keywords: {len(keywords)}\n"
                f"You'll get an early warning before this hits YouTube.",
                chat_id
            )
        except Exception as e:
            self.send(f"⚠ Could not add keyword: {e}", chat_id)

    def handle_trends(self, chat_id):
        try:
            from trends import get_manual_keywords
            keywords = get_manual_keywords(self.db_file)
            if not keywords:
                self.send(
                    "No trend keywords added yet.\n\n"
                    "Use /watch keyword to add topics to monitor on Google Trends.",
                    chat_id
                )
            else:
                kw_list = "\n".join(f"  • {kw}" for kw in keywords)
                self.send(
                    f"📈 <b>Watching {len(keywords)} keywords on Google Trends:</b>\n\n"
                    f"{kw_list}\n\n"
                    "Use /watch keyword to add more.",
                    chat_id
                )
        except Exception as e:
            self.send(f"⚠ Error: {e}", chat_id)

    def handle_setup(self, chat_id, args):
        """Load preset channels and keywords for a niche."""
        from presets import NICHES, list_niches

        if not args:
            niche_list = []
            for key, n in NICHES.items():
                niche_list.append(
                    f"/{key} — {n['name']}\n"
                    f"  {len(n['channels'])} channels · {len(n['trend_keywords'])} keywords · CPM {n['cpm_range']}"
                )
            self.send(
                "🧙 <b>SORCERER Niche Setup</b>\n\n"
                "Choose your niche and I will automatically load all the best "
                "channels and keywords for you.\n\n"
                + "\n\n".join(niche_list) +
                "\n\nSend the command to load that niche.\n"
                "Example: /full",
                chat_id
            )
            return

        niche_key = args[0].lower().lstrip("/")
        niche = NICHES.get(niche_key)

        if not niche:
            self.send(
                f"❌ Unknown niche: {niche_key}\n\n"
                "Send /setup to see available niches.",
                chat_id
            )
            return

        self.send(
            f"🧙 Loading <b>{niche['name']}</b> preset...\n\n"
            f"Adding {len(niche['channels'])} channels and "
            f"{len(niche['trend_keywords'])} trend keywords.\n\n"
            f"This will take a minute...",
            chat_id
        )

        # Add channels
        added_channels = []
        failed_channels = []
        for channel in niche["channels"]:
            if self.add_fn:
                result = self.add_fn(channel)
                if "✅" in result:
                    name = result.split("<b>")[1].split("</b>")[0] if "<b>" in result else channel
                    added_channels.append(name)
                else:
                    failed_channels.append(channel)
            import time
            time.sleep(0.5)

        # Add trend keywords
        try:
            from trends import add_manual_keywords
            add_manual_keywords(self.db_file, niche["trend_keywords"])
        except Exception as e:
            self.log_fn(f"  ⚠ Could not add trend keywords: {e}")

        # Summary
        summary = (
            f"✅ <b>{niche['name']} loaded!</b>\n\n"
            f"📡 Channels added: {len(added_channels)}\n"
            f"📈 Trend keywords added: {len(niche['trend_keywords'])}\n\n"
        )

        if added_channels:
            summary += "<b>Watching:</b>\n"
            for ch in added_channels[:10]:
                summary += f"  • {ch}\n"
            if len(added_channels) > 10:
                summary += f"  ... and {len(added_channels) - 10} more\n"

        summary += (
            f"\n💰 Expected CPM: {niche['cpm_range']}\n\n"
            f"Next scan in up to 2 hours.\n"
            f"Use /scan to run one right now."
        )

        self.send(summary, chat_id)

    def handle_direct(self, chat_id, args):
        """Run AI Director on the last generated script."""
        style = args[0].lower() if args else "hybrid"
        valid_styles = ["scorsese", "mrbeast", "capcut", "hybrid"]

        if style not in valid_styles:
            self.send(
                f"Choose a style:\n\n"
                f"/direct hybrid — Scorsese depth + MrBeast energy (recommended)\n"
                f"/direct scorsese — Pure cinematic documentary\n"
                f"/direct mrbeast — Maximum energy chaos\n"
                f"/direct capcut — Viral social media style",
                chat_id
            )
            return

        self.send(
            f"🎬 <b>AI Director is reviewing your script...</b>\n\n"
            f"Style: <b>{style.upper()}</b>\n"
            f"Analysing emotional clusters, colour narrative,\n"
            f"viral moments, replayability...\n\n"
            f"This takes about 30 seconds.",
            chat_id
        )

        # Load the most recent script from the scripts folder
        import os
        from pathlib import Path
        scripts_dir = Path(self.db_file).parent / "scripts"

        if not scripts_dir.exists():
            self.send("No scripts found yet. A script is generated automatically when SORCERER detects a viral signal.", chat_id)
            return

        script_files = sorted(scripts_dir.glob("*.md"), key=os.path.getmtime, reverse=True)
        if not script_files:
            self.send("No scripts found yet.", chat_id)
            return

        # We need the JSON version — check if there is a companion JSON
        json_scripts = sorted(Path(self.db_file).parent.glob("scripts/*.json"),
                              key=os.path.getmtime, reverse=True)

        if not json_scripts:
            self.send(
                f"Found {len(script_files)} script(s) but no JSON version to direct.\n"
                f"Scripts are automatically directed when a signal fires.",
                chat_id
            )
            return

        try:
            import json
            script = json.loads(json_scripts[0].read_text())
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

            from director import direct, format_direction_telegram
            direction = direct(
                script         = script,
                style          = style,
                target_culture = "global",
                anthropic_key  = anthropic_key,
                log_fn         = self.log_fn,
            )

            if direction and not direction.get("_error"):
                msg = format_direction_telegram(direction)
                self.send(msg or "Direction complete.", chat_id)
            else:
                self.send(f"Direction failed: {direction.get('_error','unknown error')}", chat_id)

        except Exception as e:
            self.send(f"⚠ Error: {e}", chat_id)

    def handle_approve(self, chat_id, args):
        """Approve the pending video for upload."""
        import os
        from approval import ApprovalManager
        mgr  = ApprovalManager(self.db_file, self.token, self.chat_id, self.log_fn)
        item = mgr.approve()
        if item and self.scan_fn:
            # Trigger upload in background
            threading.Thread(
                target=self._do_upload,
                args=(item, mgr),
                daemon=True
            ).start()

    def _do_upload(self, item, mgr):
        """Upload approved video to all platforms."""
        try:
            from publisher import publish_all, build_config_from_env
            import os
            config      = build_config_from_env()
            youtube_url = "https://youtube.com"
            results     = publish_all(
                master_video_path = item.get("video_path"),
                clips             = item.get("clips", {}),
                captions          = item.get("captions", {}),
                youtube_url       = youtube_url,
                config            = config,
                log_fn            = self.log_fn,
            )
            mgr.confirm_all_uploaded(item["id"], results)
        except Exception as e:
            self.send(f"⚠ Upload error: {e}", self.chat_id)

    def handle_revise(self, chat_id, args):
        """Revise the pending video."""
        if not args:
            self.send(
                "Tell me what to change.\n\n"
                "Examples:\n"
                "/revise make the hook faster\n"
                "/revise the tone is too serious, add more humor\n"
                "/revise change the opening to a shocking stat\n"
                "/revise the music feels wrong for the middle section",
                chat_id
            )
            return
        notes = " ".join(args)
        from approval import ApprovalManager
        mgr = ApprovalManager(self.db_file, self.token, self.chat_id, self.log_fn)
        mgr.revise(notes)

    def handle_restyle(self, chat_id, args):
        """Change the visual style of the pending video."""
        valid = ["scorsese", "mrbeast", "capcut", "hybrid"]
        style = args[0].lower() if args else ""
        if style not in valid:
            self.send(
                f"Choose a style:\n"
                f"/restyle hybrid — Best of all three (recommended)\n"
                f"/restyle scorsese — Pure cinematic\n"
                f"/restyle mrbeast — Maximum energy\n"
                f"/restyle capcut — Viral social",
                chat_id
            )
            return
        from approval import ApprovalManager
        mgr = ApprovalManager(self.db_file, self.token, self.chat_id, self.log_fn)
        mgr.restyle(style)

    def handle_discard(self, chat_id, args):
        """Discard the pending video."""
        from approval import ApprovalManager
        mgr = ApprovalManager(self.db_file, self.token, self.chat_id, self.log_fn)
        mgr.discard()

    def handle_preview_script(self, chat_id, args):
        """Send the full script of the pending video."""
        from approval import ApprovalManager
        mgr  = ApprovalManager(self.db_file, self.token, self.chat_id, self.log_fn)
        item = mgr.get_pending()
        if not item:
            self.send("No video pending review.", chat_id)
            return
        script   = item.get("script", {})
        sections = script.get("sections", [])
        if not sections:
            self.send("No script found for pending video.", chat_id)
            return
        # Send script in chunks
        for section in sections[:5]:
            msg = (
                f"📜 <b>[{section.get('timestamp','')}] "
                f"{section.get('name','').upper()}</b>\n\n"
                f"{section.get('narration','')[:1200]}"
            )
            self.send(msg, chat_id)
            import time
            time.sleep(0.5)

    def handle_usage(self, chat_id, args):
        """Show token usage and cost report."""
        import os
        from usage_tracker import UsageTracker
        tracker = UsageTracker(self.db_file)
        self.send(tracker.full_report_telegram(), chat_id)

    def send_video(self, video_path, caption, chat_id=None):
        """Send a video file via Telegram."""
        if not self.token:
            return
        try:
            with open(video_path, 'rb') as f:
                requests.post(
                    f"{TG_API}/bot{self.token}/sendVideo",
                    data={
                        "chat_id":    chat_id or self.chat_id,
                        "caption":    caption[:1024],
                        "parse_mode": "HTML",
                    },
                    files={"video": f},
                    timeout=120,
                )
        except Exception as e:
            self.log_fn(f"  ⚠ Telegram video send error: {e}")
            self.send(f"⚠ Could not send video file: {e}", chat_id)

    def handle_clip(self, chat_id, args):
        """Download a YouTube video and clip the best segment."""
        if not args:
            self.send(
                "✂️ <b>SORCERER Clipper</b>\n\n"
                "Send a YouTube URL and I will:\n"
                "1. Download the video\n"
                "2. AI-select the most viral 75-second segment\n"
                "3. Render vertical (9:16) + landscape (16:9) clips\n"
                "4. Send them back to you here\n\n"
                "Example: /clip https://youtube.com/watch?v=dQw4w9WgXcQ",
                chat_id
            )
            return

        url = args[0]
        self.send(
            f"✂️ <b>Clipping video...</b>\n\n"
            f"1/3 — Downloading video...\n"
            f"This may take a minute.",
            chat_id
        )

        threading.Thread(
            target=self._run_clip, args=(chat_id, url), daemon=True
        ).start()

    def _run_clip(self, chat_id, url):
        try:
            import os
            from pathlib import Path
            from downloader import download_video
            from publisher.clipper import clip_external_video

            data_dir = Path(self.db_file).parent
            dl_dir   = data_dir / "downloads"
            clip_dir = data_dir / "clips"

            # 1. Download
            video_path, info = download_video(url, str(dl_dir), log_fn=self.log_fn)
            if not video_path:
                self.send(f"❌ Download failed: {info}", chat_id)
                return

            self.send(
                f"✅ Downloaded: <b>{info.get('title','')[:50]}</b>\n\n"
                f"2/3 — AI selecting best clip segment...",
                chat_id
            )

            # 2. Clip
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
            results = clip_external_video(
                video_path, info, anthropic_key, str(clip_dir), self.log_fn
            )

            self.send(
                f"3/3 — Rendering clips...",
                chat_id
            )

            # 3. Send results
            start = results.get('start_secs', 0)
            end   = results.get('end_secs', 0)
            reason = results.get('reason', '')

            summary = (
                f"✂️ <b>CLIP COMPLETE</b>\n\n"
                f"📺 {info.get('title','')[:60]}\n"
                f"⏱ Segment: {start // 60}:{start % 60:02d} – {end // 60}:{end % 60:02d} "
                f"({end - start}s)\n"
                f"💡 Why: {reason}\n"
            )

            clip_v = results.get("clip_vertical")
            clip_l = results.get("clip_landscape")

            if clip_v:
                self.send_video(
                    clip_v,
                    f"📱 <b>Vertical clip</b> (9:16)\nTikTok / Reels ready",
                    chat_id
                )

            if clip_l:
                self.send_video(
                    clip_l,
                    f"🖥 <b>Landscape clip</b> (16:9)\nYouTube Shorts / Twitter ready",
                    chat_id
                )

            if not clip_v and not clip_l:
                summary += "\n⚠ No clips rendered — ffmpeg may not be installed."

            self.send(summary, chat_id)

            # Cleanup downloaded full video to save space
            try:
                os.remove(video_path)
            except Exception:
                pass

        except Exception as e:
            self.send(f"❌ Clip error: {e}", chat_id)

    def handle_abort(self, chat_id):
        """Abort any ongoing production."""
        self.abort_flag = True
        self.send("🛑 <b>ABORT REQUESTED</b>\nStopping production as soon as the current step finishes.", chat_id)

    def handle_produce(self, chat_id, args):
        """Full production from any YouTube URL or topic."""
        if not args:
            self.send(
                "🎬 <b>SORCERER Producer</b>\n\n"
                "Give me a YouTube URL or any topic and I will produce\n"
                "a full video package:\n\n"
                "<b>From a URL:</b>\n"
                "/produce [URL]\n\n"
                "<b>From a topic:</b>\n"
                "/produce [Topic]\n\n"
                "<b>With aspect ratio:</b>\n"
                "/produce aspect 9:16 [URL/topic]",
                chat_id
            )
            return

        self.abort_flag = False
        aspect = "16:9"
        if len(args) >= 2 and args[0].lower() == "aspect":
            aspect = args[1]
            args = args[2:]

        query = " ".join(args)
        is_url = any(p in query for p in ["youtube.com", "youtu.be", "http"])

        if is_url:
            self.send(
                f"🎬 <b>Producing from URL...</b>\n"
                f"Format: {aspect}\n\n"
                f"1/4 — Fetching video data + comments...\n"
                f"This takes about 2 minutes.",
                chat_id
            )
        else:
            self.send(
                f"🎬 <b>Producing from topic...</b>\n"
                f"Format: {aspect}\n"
                f"Topic: <b>{query[:80]}</b>\n"
                f"Generating full production package...",
                chat_id
            )

        threading.Thread(
            target=self._run_produce, 
            args=(chat_id, query, is_url), 
            kwargs={"aspect": aspect},
            daemon=True
        ).start()

    def handle_script(self, chat_id, args):
        """Produce a video verbatim from a long script text."""
        if not args:
            self.send(
                "✍️ <b>SORCERER Script Director</b>\n\n"
                "Send your full narration script after the command and I will "
                "produce it verbatim without rewriting it.\n\n"
                "<b>Syntax:</b>\n"
                "/script [Text]\n"
                "/script aspect 9:16 [Text]",
                chat_id
            )
            return

        aspect = "16:9"
        if len(args) >= 2 and args[0].lower() == "aspect":
            aspect = args[1]
            args = args[2:]

        query = " ".join(args)
        self.send(
            f"✍️ <b>Producing from verbatim script...</b>\n"
            f"Format: {aspect}\n"
            f"Length: {len(query)} characters\n"
            f"Bypassing AI scriptwriter, going straight to production...",
            chat_id
        )

        threading.Thread(
            target=self._run_produce, 
            args=(chat_id, query, False, True), 
            kwargs={"aspect": aspect},
            daemon=True
        ).start()

    def _run_produce(self, chat_id, query, is_url, force_verbatim=False, aspect="16:9"):
        try:
            if self.abort_flag: return
            import os
            from pathlib import Path
            from pipeline import produce, build_config_from_env

            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
            yt_key        = os.getenv("YOUTUBE_API_KEY", "")
            config        = build_config_from_env()

            if not anthropic_key:
                self.send("❌ No ANTHROPIC_API_KEY — production requires Claude.", chat_id)
                return

            is_exact_text = False
            video    = {}
            comments = []
            signal   = {"level": "ON-DEMAND", "emoji": "🎬", "multiplier": 0, "window": "manual"}
            baseline = {"median_vph": 0, "median_duration": 15, "mean_vph": 0, "stdev_vph": 0, "sample_size": 1}

            if is_url:
                # ── URL mode: fetch data ──
                vid_id = query
                for pattern in ["watch?v=", "youtu.be/", "shorts/"]:
                    if pattern in query:
                        vid_id = query.split(pattern)[-1].split("&")[0].split("?")[0]
                        break

                if not yt_key:
                    self.send("❌ No YOUTUBE_API_KEY — cannot fetch video data.", chat_id)
                    return

                import requests as req
                from datetime import datetime, timezone
                data = req.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "key":  yt_key,
                        "part": "statistics,snippet,contentDetails",
                        "id":   vid_id,
                    },
                    timeout=15,
                ).json()

                if not data.get("items"):
                    self.send("❌ Video not found — check the URL.", chat_id)
                    return

                item   = data["items"][0]
                pub_dt = datetime.fromisoformat(
                    item["snippet"]["publishedAt"].replace("Z", "+00:00")
                )
                age_h  = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
                views  = int(item["statistics"].get("viewCount", 0))

                from engine import parse_iso_duration, fetch_comments
                video = {
                    "id":            vid_id,
                    "title":         item["snippet"]["title"],
                    "channel_title": item["snippet"]["channelTitle"],
                    "channel_id":    item["snippet"]["channelId"],
                    "age_hours":     round(age_h, 1),
                    "views":         views,
                    "likes":         int(item["statistics"].get("likeCount", 0)),
                    "comment_count": int(item["statistics"].get("commentCount", 0)),
                    "views_per_hour": round(views / max(age_h, 0.5), 1),
                    "duration_mins": parse_iso_duration(
                        item["contentDetails"].get("duration", "PT0S")
                    ),
                }

                self.send(
                    f"📺 <b>{video['title'][:60]}</b>\n"
                    f"{video['channel_title']} · {video['views']:,} views\n\n"
                    f"2/5 — Running production pipeline...",
                    chat_id
                )

                comments = fetch_comments(vid_id, yt_key)
                baseline["median_vph"] = video["views_per_hour"]
                baseline["median_duration"] = video["duration_mins"]

            else:
                # ── Topic / Text mode ──
                if force_verbatim or len(query) > 200:
                    is_exact_text = True
                    if not force_verbatim:
                        self.send("📝 Received raw text format. Using exact text as script narration.", chat_id)

                video = {
                    "id":            "topic",
                    "title":         query,  # FIX: removed [:300] truncation
                    "channel_title": "Your Channel",
                    "channel_id":    "",
                    "age_hours":     0,
                    "views":         0,
                    "likes":         0,
                    "comment_count": 0,
                    "views_per_hour": 0,
                    "duration_mins": max(1, len(query.split()) // 150),
                }

            # ── Run Full Pipeline ──
            self.send("🎬 Beginning full video extraction and synthesis. This takes roughly 15-20 minutes depending on length and footage.", chat_id)
            
            results = produce(
                video, signal, baseline, comments, config, 
                log_fn=self.log_fn, 
                is_exact_text=is_exact_text,
                aspect_ratio=aspect
            )

            if not results.get("script_file"):
                self.send("❌ Production failed during script generation stage.", chat_id)
                return

            # ── Final Deliverables Summary ──
            self.send(f"✅ <b>PRODUCTION COMPLETE</b>\nDelivering assets...", chat_id)

            # 1. Provide Thumbnail stuff
            t_plan = results.get("thumbnail_plan")
            t_file = results.get("thumbnail_file")

            if t_plan:
                # Send the blueprint
                self.send(t_plan, chat_id)
            
            if t_file and os.path.exists(t_file):
                # Send the physical thumbnail image extracted from YT
                try:
                    import requests
                    TG_API = "https://api.telegram.org"
                    with open(t_file, 'rb') as f:
                        requests.post(
                            f"{TG_API}/bot{self.token}/sendPhoto",
                            data={
                                "chat_id": chat_id,
                                "caption": "Downloaded original YouTube thumbnail.",
                            },
                            files={"photo": f},
                        )
                except Exception as e:
                    self.log_fn(f"Failed to send thumbnail photo: {e}")

            # 2. Provide Master Video
            master_vid = results.get("video_file")
            if master_vid and os.path.exists(master_vid):
                self.send_video(master_vid, "🎥 <b>MASTER VIDEO</b>\nFull cinematic documentary.", chat_id)
            elif not config.get("elevenlabs_key"):
                self.send("⚠ <b>Script-Only Mode</b>: ELEVENLABS_API_KEY was not set so the pipeline stopped before video generation.", chat_id)

            # 3. Provide Clips
            clips = results.get("clips", {})
            clip_v = clips.get("clip_vertical")
            clip_l = clips.get("clip_landscape")
            
            if clip_v and os.path.exists(clip_v):
                self.send_video(clip_v, "📱 <b>VERTICAL VIRAL CLIP</b>\n9:16 ratio for TikTok / Reels.", chat_id)
            if clip_l and os.path.exists(clip_l):
                self.send_video(clip_l, "🖥 <b>LANDSCAPE VIRAL CLIP</b>\n16:9 ratio for Twitter / Shorts.", chat_id)

            # Last summary message
            self.send(
                f"🧙 <b>PACKAGE DELIVERED</b>\n\n"
                f"📝 Use /preview_script to read the full script markdown.\n"
                f"Use /approve to auto-publish (if 3rd-party keys configured).",
                chat_id
            )

        except Exception as e:
            self.send(f"❌ Production error: {e}", chat_id)

    def handle_concept(self, chat_id, args):
        """Generate wild viral series concepts or pick one for a full bible."""
        import os

        # /concept pick N — generate series bible for concept N
        if args and args[0].lower() == "pick":
            pick_num = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
            if not hasattr(self, '_last_concepts') or not self._last_concepts:
                self.send("No concepts generated yet. Send /concept first.", chat_id)
                return
            if pick_num < 1 or pick_num > len(self._last_concepts):
                self.send(f"Pick a number between 1 and {len(self._last_concepts)}.", chat_id)
                return

            chosen = self._last_concepts[pick_num - 1]
            self.send(
                f"📖 Generating full series bible for:\n"
                f"<b>{chosen.get('title', '?')}</b>\n\n"
                f"This takes about 60 seconds...",
                chat_id
            )
            threading.Thread(
                target=self._run_bible, args=(chat_id, chosen), daemon=True
            ).start()
            return

        # /concept [niche] — generate new concepts
        niche_hint = " ".join(args) if args else None
        self.send(
            f"🧪 <b>Concept Lab firing up...</b>\n\n"
            f"Generating 5 wild viral series ideas"
            + (f" in the <b>{niche_hint}</b> space" if niche_hint else "") +
            f"\nThis takes about 30 seconds.",
            chat_id
        )
        threading.Thread(
            target=self._run_concepts, args=(chat_id, niche_hint), daemon=True
        ).start()

    def _run_concepts(self, chat_id, niche_hint):
        try:
            import os
            from concept_lab import generate_concepts, format_concepts_telegram
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
            concepts = generate_concepts(
                anthropic_key, niche_hint=niche_hint, n=5, log_fn=self.log_fn
            )
            if isinstance(concepts, dict) and concepts.get("_error"):
                self.send(f"❌ {concepts['_error']}", chat_id)
                return
            self._last_concepts = concepts
            msg = format_concepts_telegram(concepts)
            # Telegram has a 4096 char limit — split if needed
            if len(msg) > 4000:
                parts = msg.split("─────────────────────────")
                for part in parts:
                    if part.strip():
                        self.send(part.strip(), chat_id)
                        import time
                        time.sleep(0.5)
            else:
                self.send(msg, chat_id)
        except Exception as e:
            self.send(f"❌ Concept Lab error: {e}", chat_id)

    def _run_bible(self, chat_id, concept):
        try:
            import os
            from concept_lab import generate_series_bible, format_bible_telegram
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
            bible = generate_series_bible(concept, anthropic_key, log_fn=self.log_fn)
            if isinstance(bible, dict) and bible.get("_error"):
                self.send(f"❌ {bible['_error']}", chat_id)
                return
            self._last_bible = bible
            msg = format_bible_telegram(bible)
            if len(msg) > 4000:
                # Split at section breaks
                mid = len(msg) // 2
                self.send(msg[:mid], chat_id)
                import time
                time.sleep(0.5)
                self.send(msg[mid:], chat_id)
            else:
                self.send(msg, chat_id)
        except Exception as e:
            self.send(f"❌ Series bible error: {e}", chat_id)

    def handle_conceive(self, chat_id, args):
        """Generate a concept and immediately produce the pilot episode."""
        import os

        # If a number is provided, use that concept from the last batch
        if args and args[0].isdigit():
            pick_num = int(args[0])
            if not hasattr(self, '_last_concepts') or not self._last_concepts:
                self.send("No concepts generated yet. Send /concept first.", chat_id)
                return
            if pick_num < 1 or pick_num > len(self._last_concepts):
                self.send(f"Pick a number between 1 and {len(self._last_concepts)}.", chat_id)
                return
            chosen = self._last_concepts[pick_num - 1]
            self.send(
                f"🚀 <b>CONCEIVE MODE</b>\n\n"
                f"Generating series bible + producing pilot episode for:\n"
                f"<b>{chosen.get('title', '?')}</b>\n\n"
                f"This takes about 15-20 minutes total.",
                chat_id
            )
            threading.Thread(
                target=self._run_conceive, args=(chat_id, chosen), daemon=True
            ).start()
            return

        # If a bible was already generated, produce from that
        if hasattr(self, '_last_bible') and self._last_bible:
            self.send(
                f"🚀 <b>Producing pilot episode from last series bible...</b>\n\n"
                f"This takes about 15-20 minutes.",
                chat_id
            )
            threading.Thread(
                target=self._run_conceive_from_bible, args=(chat_id, self._last_bible), daemon=True
            ).start()
            return

        self.send(
            "🧪 <b>Conceive Mode</b>\n\n"
            "Generate concepts first, then conceive:\n"
            "1. /concept — generate 5 ideas\n"
            "2. /conceive 1 — produce pilot for idea #1\n\n"
            "Or if you already have a series bible:\n"
            "/conceive — produces the last bible's pilot",
            chat_id
        )

    def _run_conceive(self, chat_id, concept):
        """Generate bible then produce pilot."""
        try:
            import os
            from concept_lab import generate_series_bible, extract_pilot_as_script, format_bible_telegram
            from pipeline import produce, build_config_from_env

            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

            # Step 1: Generate bible
            self.send("📖 Step 1/2 — Generating series bible...", chat_id)
            bible = generate_series_bible(concept, anthropic_key, log_fn=self.log_fn)
            if isinstance(bible, dict) and bible.get("_error"):
                self.send(f"❌ Bible generation failed: {bible['_error']}", chat_id)
                return
            self._last_bible = bible

            # Send bible summary
            bible_msg = format_bible_telegram(bible)
            if len(bible_msg) > 4000:
                mid = len(bible_msg) // 2
                self.send(bible_msg[:mid], chat_id)
                import time
                time.sleep(0.5)
                self.send(bible_msg[mid:], chat_id)
            else:
                self.send(bible_msg, chat_id)

            # Step 2: Produce pilot
            self._run_conceive_from_bible(chat_id, bible)

        except Exception as e:
            self.send(f"❌ Conceive error: {e}", chat_id)

    def _run_conceive_from_bible(self, chat_id, bible):
        """Produce the pilot episode from a series bible."""
        try:
            import os
            from concept_lab import extract_pilot_as_script
            from pipeline import produce, build_config_from_env

            pilot_script = extract_pilot_as_script(bible)
            if not pilot_script or not pilot_script.get("sections"):
                self.send("❌ No pilot script found in the series bible.", chat_id)
                return

            self.send(
                f"🎬 Step 2/2 — Producing pilot episode...\n\n"
                f"Title: <b>{pilot_script.get('title', '?')}</b>\n"
                f"This takes about 15-20 minutes.",
                chat_id
            )

            # Build a mock video/signal/baseline for the pipeline
            title = pilot_script.get("title", "Concept Lab Pilot")
            video = {
                "id":            "concept",
                "title":         title,
                "channel_title": bible.get("series_bible", {}).get("channel_names", ["Concept Lab"])[0],
                "channel_id":    "",
                "age_hours":     0,
                "views":         0,
                "likes":         0,
                "comment_count": 0,
                "views_per_hour": 0,
                "duration_mins": pilot_script.get("estimated_runtime_mins", 3),
            }
            signal   = {"level": "CONCEPT", "emoji": "🧪", "multiplier": 0, "window": "concept"}
            baseline = {"median_vph": 0, "median_duration": 3, "mean_vph": 0, "stdev_vph": 0, "sample_size": 1}
            config   = build_config_from_env()

            results = produce(
                video, signal, baseline, [], config,
                log_fn=self.log_fn,
                is_exact_text=False,
            )

            if not results.get("script_file"):
                self.send("❌ Production failed during pipeline.", chat_id)
                return

            # Deliver results
            self.send(f"✅ <b>PILOT EPISODE PRODUCED</b>\nDelivering assets...", chat_id)

            master_vid = results.get("video_file")
            if master_vid and os.path.exists(master_vid):
                self.send_video(master_vid, "🎥 <b>PILOT EPISODE</b>\nYour first episode.", chat_id)

            clips = results.get("clips", {})
            clip_v = clips.get("clip_vertical")
            if clip_v and os.path.exists(clip_v):
                self.send_video(clip_v, "📱 <b>VERTICAL CLIP</b>\n9:16 for TikTok / Reels.", chat_id)

            self.send(
                f"🧙 <b>CONCEPT LAB — COMPLETE</b>\n\n"
                f"Your pilot episode for <b>{title[:50]}</b> is ready.\n"
                f"Use /preview_script to read the full script.",
                chat_id
            )

        except Exception as e:
            self.send(f"❌ Production error: {e}", chat_id)

    def handle_status(self, chat_id):
        db    = self.load_db()
        last  = db.get("last_scan")
        scans = db.get("scans", 0)
        total = db.get("total_alerts", 0)
        chans = len(db.get("channels", {}))
        kws   = len(db.get("trend_keywords", []))
        if last:
            ago  = datetime.now() - datetime.fromisoformat(last)
            h, m = int(ago.total_seconds() / 3600), int((ago.total_seconds() % 3600) / 60)
            last_str = f"{h}h {m}m ago"
        else:
            last_str = "never"
        self.send(
            f"🧙 <b>SORCERER Status</b>\n\n"
            f"🟢 Running on Railway\n"
            f"📡 YouTube channels: {chans}\n"
            f"📈 Trend keywords: {kws}\n"
            f"🔍 Last scan: {last_str}\n"
            f"📊 Total scans: {scans}\n"
            f"🔥 Total alerts fired: {total}\n\n"
            f"Scanning every 2 hours automatically.",
            chat_id
        )

    def process(self, message):
        chat_id = str(message.get("chat", {}).get("id", ""))
        text    = message.get("text", "").strip()
        if chat_id != self.chat_id:
            self.send("⛔ Unauthorised.", chat_id)
            return
        if not text:
            return
        parts   = text.split()
        command = parts[0].lower().split("@")[0]
        args    = parts[1:]
        handlers = {
            "/start":       lambda: self.handle_start(chat_id),
            "/help":        lambda: self.handle_help(chat_id),
            "/list":        lambda: self.handle_list(chat_id),
            "/add":         lambda: self.handle_add(chat_id, args),
            "/remove":      lambda: self.handle_remove(chat_id, args),
            "/scan":        lambda: self.handle_scan(chat_id),
            "/watch":       lambda: self.handle_watch(chat_id, args),
            "/trends":      lambda: self.handle_trends(chat_id),
            "/status":      lambda: self.handle_status(chat_id),
            "/setup":       lambda: self.handle_setup(chat_id, args),
            "/ai_tech":     lambda: self.handle_setup(chat_id, ["ai_tech"]),
            "/ai_healthcare": lambda: self.handle_setup(chat_id, ["ai_healthcare"]),
            "/ai_innovation": lambda: self.handle_setup(chat_id, ["ai_innovation"]),
            "/ai":             lambda: self.handle_setup(chat_id, ["ai"]),
            "/innovation":     lambda: self.handle_setup(chat_id, ["innovation"]),
            "/tech":           lambda: self.handle_setup(chat_id, ["tech"]),
            "/invention":      lambda: self.handle_setup(chat_id, ["invention"]),
            "/hi_weapons":     lambda: self.handle_setup(chat_id, ["hi_weapons"]),
            "/money":          lambda: self.handle_setup(chat_id, ["money"]),
            "/full":           lambda: self.handle_setup(chat_id, ["full"]),
            "/direct":         lambda: self.handle_direct(chat_id, args),
            "/scorsese":       lambda: self.handle_direct(chat_id, ["scorsese"]),
            "/mrbeast":        lambda: self.handle_direct(chat_id, ["mrbeast"]),
            "/capcut":         lambda: self.handle_direct(chat_id, ["capcut"]),
            "/hybrid":         lambda: self.handle_direct(chat_id, ["hybrid"]),
            "/approve":        lambda: self.handle_approve(chat_id, args),
            "/usage":          lambda: self.handle_usage(chat_id, args),
            "/cost":           lambda: self.handle_usage(chat_id, args),
            "/revise":         lambda: self.handle_revise(chat_id, args),
            "/restyle":        lambda: self.handle_restyle(chat_id, args),
            "/discard":        lambda: self.handle_discard(chat_id, args),
            "/preview_script": lambda: self.handle_preview_script(chat_id, args),
            "/clip":           lambda: self.handle_clip(chat_id, args),
            "/produce":        lambda: self.handle_produce(chat_id, args),
            "/script":         lambda: self.handle_script(chat_id, args),
            "/abort":          lambda: self.handle_abort(chat_id),
            "/concept":        lambda: self.handle_concept(chat_id, args),
            "/conceive":       lambda: self.handle_conceive(chat_id, args),
        }
        handler = handlers.get(command)
        if handler:
            handler()
        else:
            self.send("I don't know that command.\nSend /help to see what I can do.", chat_id)

    def start_polling(self):
        self.running = True
        self.log_fn("  📱 Telegram bot listening for commands...")
        while self.running:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.offset = update["update_id"] + 1
                    message = update.get("message") or update.get("edited_message")
                    if message:
                        self.process(message)
            except Exception as e:
                self.log_fn(f"  ⚠ Bot polling error: {e}")
                time.sleep(5)

    def start_in_background(self):
        t = threading.Thread(target=self.start_polling, daemon=True)
        t.start()
        return t

    def stop(self):
        self.running = False
