#!/usr/bin/env python3
"""
SORCERER Telegram Bot — Remote control for the YouTube intelligence agent.
Enhanced with niche presets and persistent menu.
"""

import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
import re

try:
    import requests
except ImportError:
    print("Run: pip install requests")
    raise

import presets

class SorcererBot:
    """Telegram bot for remote SORCERER control."""
    
    def __init__(self, token, chat_id, db_file, log_fn=None):
        self.token = token
        self.chat_id = chat_id
        self.db_file = Path(db_file)
        self.log_fn = log_fn or print
        
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.running = False
        self.thread = None
        
        # Functions injected by sorcerer.py
        self.scan_fn = None
        self.add_fn = None
        self.remove_fn = None
        self.list_fn = None
        self.status_fn = None
        self.usage_fn = None
        self.watch_fn = None
        self.trends_fn = None
        self.script_fn = None
        self.screen_fn = None
        self.pause_fn  = None
        self.resume_fn = None
        self.resolve_video_fn = None  # Injected by sorcerer.py for URL-based /assets
        
        # Track video data by alert message ID so /assets can work via reply
        self.alert_videos = {}  # {message_id: video_data}
        self.focus_video = None
        self.offset = 0
        
    def send(self, message, reply_markup=None):
        """Send a message and return message_id for tracking."""
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        try:
            resp = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
            if resp.ok:
                return resp.json().get("result", {}).get("message_id")
        except Exception as e:
            self.log_fn(f"  ⚠ Telegram send error: {e}")
        return None

    def set_focus(self, video_data):
        """Update the currently focused video (radar auto-sets this, or reply-based)."""
        self.focus_video = video_data
        self.log_fn(f"  🎯 Bot focus set to: {video_data['title']}")

    def register_alert_video(self, message_id, video_data):
        """Store video data keyed by the alert message_id so reply-based /assets works."""
        if message_id:
            self.alert_videos[message_id] = video_data
            # Keep dict bounded — drop oldest entries beyond 50
            if len(self.alert_videos) > 50:
                oldest = sorted(self.alert_videos.keys())[0]
                del self.alert_videos[oldest]

    def get_main_menu(self):
        """Persistent keyboard for common actions."""
        return {
            "keyboard": [
                ["/scan", "/status"],
                ["/list", "/usage"],
                ["/trends", "/setup"],
                ["/pause", "/resume"],
                ["/help"]
            ],
            "resize_keyboard": True,
            "persistent": True
        }

    def start_in_background(self):
        """Start polling in background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        self.send("🧙 <b>SORCERER ONLINE</b>\nSignals detected in real-time. Use the menu below to control.", self.get_main_menu())

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _poll_loop(self):
        while self.running:
            try:
                self._fetch_and_handle_updates()
            except Exception as e:
                self.log_fn(f"  ⚠ Bot polling error: {e}")
            time.sleep(1)

    def _fetch_and_handle_updates(self):
        try:
            resp = requests.get(f"{self.api_url}/getUpdates", params={"offset": self.offset, "timeout": 10}, timeout=15)
            if not resp.ok: return
            data = resp.json()
            if not data.get("ok"): return
            
            for update in data.get("result", []):
                self.offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg: continue
                text = msg.get("text", "").strip()
                
                # Capture reply context so /assets can resolve the right video
                reply_to_msg = msg.get("reply_to_message")
                
                if text:
                    try:
                        self._handle_message(text, msg.get("message_id"), reply_to_msg)
                    except Exception as e:
                        self.log_fn(f"  ⚠ Handler error for '{text}': {e}")
                        self.send(f"❌ Error handling command: {e}")
        except Exception as e:
            self.log_fn(f"  ⚠ Poll error: {e}")

    def _handle_message(self, text, msg_id=None, reply_to_msg=None):
        cmd = text.split()[0].lower() if text.startswith("/") else ""
        cmd = cmd.split("@")[0]  # strip @BotUsername Telegram appends in reply context
        
        if cmd in ("/start", "/help"):
            self._cmd_help()
        elif cmd == "/scan":
            self._cmd_scan()
        elif cmd == "/list":
            self._cmd_list()
        elif cmd == "/status":
            self._cmd_status()
        elif cmd == "/usage":
            self._cmd_usage()
        elif cmd == "/setup":
            self._cmd_setup_menu()
        elif cmd == "/full":
            threading.Thread(target=self._apply_niche, args=("full",), daemon=True).start()
        elif cmd == "/reseed":
            threading.Thread(target=self._apply_niche, args=("full",), daemon=True).start()
        elif cmd in [f"/{k}" for k in presets.NICHES.keys()]:
            threading.Thread(target=self._apply_niche, args=(cmd[1:],), daemon=True).start()
        elif text.startswith("/add "):
            self._cmd_add(text[5:].strip())
        elif text.startswith("/remove "):
            self._cmd_remove(text[8:].strip())
        elif cmd == "/trends":
            if self.trends_fn:
                self.send(self.trends_fn())
            else:
                self.send("📊 <b>Google Trends Radar</b>\nUse <code>/watch [keyword]</code> to add topics.")
        elif cmd == "/voice":
            self._cmd_voice_menu()
        elif cmd == "/pause":
            self._cmd_pause()
        elif cmd == "/resume":
            self._cmd_resume()
        elif cmd == "/assets":
            self._cmd_assets_menu(text, reply_to_msg)
        elif cmd == "/screen":
            self._cmd_screen(text, reply_to_msg)
        elif cmd == "/resp_short":
            self._generate_resp("resp_short")
        elif cmd == "/resp_med":
            self._generate_resp("resp_med")
        elif cmd == "/resp_long":
            self._generate_resp("resp_long")
        elif cmd == "/resp_hour":
            self._generate_resp("resp_hour")
        elif text.startswith("/watch "):
            if self.watch_fn:
                res = self.watch_fn(text[7:].strip())
                self.send(res)
            else:
                self.send(f"👁 Now watching trend: <b>{text[7:].strip()}</b>")
        else:
            self.send("❓ Unknown command. Send /help for options.", self.get_main_menu())

    # ── Help ─────────────────────────────────────────────────────────────────
    def _cmd_help(self):
        msg = (
            "🧙 <b>SORCERER Commands</b>\n\n"
            "<b>Quick Setup</b>\n"
            "/setup — Load preset niche channels\n"
            "/full — Load ALL channels (15+ signals)\n\n"
            "<b>YouTube Radar</b>\n"
            "/scan — Run a full scan right now\n"
            "/add @channel — Add a channel\n"
            "/remove name — Stop watching\n"
            "/list — See all channels monitored\n"
            "/pause — ⏸ Pause radar (zero cost)\n"
            "/resume — ▶️ Resume radar\n\n"
            "<b>Google Trends</b>\n"
            "/watch keyword — Monitor a topic\n"
            "/trends — See all active keywords\n\n"
            "<b>Response Assets</b>\n"
            "/assets [url] — Scripts (2:50 / 6m / 15m / 1hr) + screenshots\n"
            "  ↳ Reply to a signal <i>or</i> paste any YouTube URL\n"
            "/screen [url] — Key frames to grab from target video\n\n"
            "<b>Reporting & Info</b>\n"
            "/status — Operational health report\n"
            "/usage — Token usage and cost report\n"
            "/help — Show this message"
        )
        self.send(msg, self.get_main_menu())

    # ── Radar commands ────────────────────────────────────────────────────────
    def _cmd_scan(self):
        if not self.scan_fn: return
        self.send("📡 <b>Scanning radar signals...</b> (results will appear shortly)")
        def do_scan():
            try:
                found = self.scan_fn()
                self.send(f"✅ Scan complete. Found <b>{found}</b> new signals.")
            except Exception as e:
                self.send(f"❌ Scan error: {e}")
        threading.Thread(target=do_scan, daemon=True).start()

    def _cmd_list(self):
        if not self.list_fn: return
        self.send(self.list_fn())

    def _cmd_status(self):
        if not self.status_fn: return
        self.send(self.status_fn())

    def _cmd_usage(self):
        if not self.usage_fn:
            self.send("📊 <b>Usage Report</b>\nNo data logged for current period.")
            return
        self.send(self.usage_fn())

    def _cmd_pause(self):
        if self.pause_fn:
            self.send(self.pause_fn(), self.get_main_menu())
        else:
            self.send("⏸ Radar pause not available in this mode.")

    def _cmd_resume(self):
        if self.resume_fn:
            self.send(self.resume_fn(), self.get_main_menu())
        else:
            self.send("▶️ Radar resume not available in this mode.")

    def _cmd_setup_menu(self):
        msg = "🎯 <b>Select your Niche Presets</b>\n\n" + presets.list_niches()
        msg += "\n\n<i>Click a command above to activate.</i>"
        self.send(msg)

    def _apply_niche(self, niche_key):
        niche = presets.get_niche(niche_key)
        if not niche: return
        
        total = len(niche['channels'])
        self.send(f"🏗 <b>Loading {niche['name']}...</b>\n<i>Resolving {total} channels via YouTube API. This may take 2-5 minutes.</i>")
        added = 0
        skipped = 0
        failed = 0
        for i, channel in enumerate(niche['channels'], 1):
            if self.add_fn:
                try:
                    res = self.add_fn(channel)
                    if "Added" in res:
                        added += 1
                    elif "Already" in res:
                        skipped += 1
                    else:
                        failed += 1
                    if i % 10 == 0:
                        self.send(f"⏳ Progress: {i}/{total} channels processed...")
                except Exception:
                    failed += 1
        
        self.send(
            f"✅ <b>Setup Complete</b>\n"
            f"Channels added : {added}\n"
            f"Already on radar: {skipped}\n"
            f"Failed to resolve: {failed}\n\n"
            f"<i>Send /list to see your full radar.</i>",
            self.get_main_menu()
        )

    def _cmd_add(self, query):
        if not self.add_fn: return
        self.send(f"🔍 <b>Resolving:</b> {query}...")
        res = self.add_fn(query)
        self.send(res)

    def _cmd_remove(self, query):
        if not self.remove_fn: return
        res = self.remove_fn(query)
        self.send(res)

    # ── Voice / assets ────────────────────────────────────────────────────────
    def _cmd_voice_menu(self):
        if not self.focus_video:
            self.send("❌ <b>No target video.</b>\nReply to a signal alert with /assets or paste a URL.")
            return
        
        msg = (
            f"🎙 <b>Response Script Generator</b>\n"
            f"Target: <i>{self.focus_video['title']}</i>\n\n"
            f"Choose your response duration:"
        )
        markup = {
            "keyboard": [
                ["/resp_short (2m 50s)", "/resp_med (6m)"],
                ["/resp_long (15m)", "/resp_hour (1hr)"],
                ["/screen", "/help"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        self.send(msg, markup)

    @staticmethod
    def _extract_video_id(text):
        """Pull a YouTube video ID out of a URL or bare 11-char ID."""
        for pattern in ["watch?v=", "youtu.be/", "shorts/", "embed/"]:
            if pattern in text:
                raw = text.split(pattern)[-1].split("&")[0].split("?")[0].strip()
                return raw[:11] if len(raw) >= 11 else None
        # Bare 11-char ID
        match = re.search(r'\b([A-Za-z0-9_-]{11})\b', text)
        return match.group(1) if match else None

    def _resolve_target_video(self, text, reply_to_msg):
        """
        Determine which video to act on using this priority:
          1. URL/ID in the command text itself  (/assets https://...)
          2. Replied-to alert message in alert_videos registry
          3. self.focus_video already set by the radar
        Returns video_data dict or None.
        """
        # 1. Inline URL
        vid_id = self._extract_video_id(text)
        if vid_id and self.resolve_video_fn:
            video = self.resolve_video_fn(vid_id)
            if video:
                self.set_focus(video)
                return video

        # 2. Reply context
        if reply_to_msg:
            alert_msg_id = reply_to_msg.get("message_id")
            if alert_msg_id in self.alert_videos:
                video = self.alert_videos[alert_msg_id]
                self.set_focus(video)
                return video
            # Also try to extract ID from the text of the replied-to message
            replied_text = reply_to_msg.get("text", "")
            vid_id = self._extract_video_id(replied_text)
            if vid_id and self.resolve_video_fn:
                video = self.resolve_video_fn(vid_id)
                if video:
                    self.set_focus(video)
                    return video

        # 3. Last radar-detected focus
        return self.focus_video

    def _cmd_assets_menu(self, text="", reply_to_msg=None):
        video = self._resolve_target_video(text, reply_to_msg)

        if not video:
            self.send(
                "❌ <b>No target video found.</b>\n\n"
                "Three ways to use /assets:\n"
                "1️⃣ Reply to a viral signal alert with /assets\n"
                "2️⃣ /assets https://youtube.com/watch?v=...\n"
                "3️⃣ Run /scan — the next signal auto-loads the target"
            )
            return

        msg = (
            f"🎬 <b>Response Assets</b>\n"
            f"📺 <i>{video['title'][:60]}</i>\n\n"
            f"<b>Voiceover script — choose length:</b>\n"
            f"• /resp_short — 2 min 50 sec\n"
            f"• /resp_med — 6 minutes\n"
            f"• /resp_long — 15 minutes\n"
            f"• /resp_hour — 1 hour (deep-dive)\n\n"
            f"<b>Visual assets:</b>\n"
            f"• /screen — Key frames to screenshot from source video"
        )
        markup = {
            "keyboard": [
                ["/resp_short", "/resp_med"],
                ["/resp_long", "/resp_hour"],
                ["/screen", "/help"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        self.send(msg, markup)

    def _cmd_screen(self, text="", reply_to_msg=None):
        video = self._resolve_target_video(text, reply_to_msg)

        if not video:
            self.send(
                "❌ <b>No target video.</b>\n\n"
                "Usage:\n"
                "• Reply to a signal alert with /screen\n"
                "• /screen https://youtube.com/watch?v=...\n"
                "• Run /assets first to lock a target"
            )
            return

        if not self.screen_fn:
            self.send("❌ Screen asset generator not configured.")
            return

        self.send(
            f"🔍 <b>Analyzing video for key visual moments...</b>\n"
            f"<i>{video['title'][:50]}</i>\n"
            f"<i>Identifying the best frames to screenshot and crop. ~30 sec</i>"
        )

        def run():
            try:
                result = self.screen_fn(video)
                self.send(result, self.get_main_menu())
            except Exception as e:
                self.send(f"❌ Error: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _generate_resp(self, length):
        if not self.script_fn or not self.focus_video:
            self.send("❌ Cannot generate script — no target video locked. Use /assets first.")
            return

        label = {
            "resp_short": "2 min 50 sec",
            "resp_med":   "6 minute",
            "resp_long":  "15 minute",
            "resp_hour":  "1 hour deep-dive",
        }.get(length, length)

        self.send(f"✍ <b>Generating {label} response script...</b>\nThis may take 30–90 seconds.")

        def run():
            try:
                res = self.script_fn(self.focus_video, length)
                if res:
                    self.send(res, self.get_main_menu())
                else:
                    self.send("❌ Script generation failed.")
            except Exception as e:
                self.send(f"❌ Error: {e}")

        threading.Thread(target=run, daemon=True).start()
