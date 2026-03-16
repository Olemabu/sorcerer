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
            "<b>Info</b>\n"
            "/status — How SORCERER is doing\n\n"
            "<b>AI Director</b>\n"
            "/direct — Direct your last script\n"
            "/scorsese /mrbeast /capcut /hybrid\n\n"
            "<b>Review & Publish</b>\n"
            "/approve — Upload video to all platforms\n"
            "/revise [notes] — Change something\n"
            "/restyle [style] — New visual style\n"
            "/preview_script — Read the full script\n"
            "/discard — Scrap this video\n\n"
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
            results = self.scan_fn()
            if results == 0:
                self.send("✅ Scan complete — all quiet. No new signals.", chat_id)
            else:
                self.send(f"🔥 Scan complete — {results} new signal(s) detected! Check above.", chat_id)
        except Exception as e:
            self.send(f"⚠ Scan error: {e}", chat_id)

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
            "/full":        lambda: self.handle_setup(chat_id, ["full"]),
            "/direct":         lambda: self.handle_direct(chat_id, args),
            "/scorsese":       lambda: self.handle_direct(chat_id, ["scorsese"]),
            "/mrbeast":        lambda: self.handle_direct(chat_id, ["mrbeast"]),
            "/capcut":         lambda: self.handle_direct(chat_id, ["capcut"]),
            "/hybrid":         lambda: self.handle_direct(chat_id, ["hybrid"]),
            "/approve":        lambda: self.handle_approve(chat_id, args),
            "/revise":         lambda: self.handle_revise(chat_id, args),
            "/restyle":        lambda: self.handle_restyle(chat_id, args),
            "/discard":        lambda: self.handle_discard(chat_id, args),
            "/preview_script": lambda: self.handle_preview_script(chat_id, args),
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
