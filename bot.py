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
        self.script_fn = None  # Injected script generator
        self.screen_fn = None  # Injected screen asset generator
        
        self.focus_video = None  # Locks onto the latest detected/added video
        self.offset = 0
        
    def send(self, message, reply_markup=None):
        """Send a message to the configured chat with optional keyboard."""
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        try:
            requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
        except Exception as e:
            self.log_fn(f"  ⚠ Telegram send error: {e}")

    def set_focus(self, video_data):
        """Update the currently focused video (for /voice and /screen commands)."""
        self.focus_video = video_data
        self.log_fn(f"  🎯 Bot focus set to: {video_data['title']}")

    def get_main_menu(self):
        """Persistent keyboard for common actions."""
        return {
            "keyboard": [
                ["/scan", "/status"],
                ["/list", "/usage"],
                ["/trends", "/setup"],
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
                if text:
                    try:
                        self._handle_message(text)
                    except Exception as e:
                        self.log_fn(f"  ⚠ Handler error for '{text}': {e}")
                        self.send(f"❌ Error handling command: {e}")
        except Exception as e:
            self.log_fn(f"  ⚠ Poll error: {e}")

    def _handle_message(self, text):
        cmd = text.split()[0].lower() if text.startswith("/") else ""
        
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
        elif cmd == "/screen":
            self._cmd_screen()
        elif cmd == "/resp_short":
            self._generate_resp("resp_short")
        elif cmd == "/resp_med":
            self._generate_resp("resp_med")
        elif cmd == "/resp_long":
            self._generate_resp("resp_long")
        elif text.startswith("/watch "):
            if self.watch_fn:
                res = self.watch_fn(text[7:].strip())
                self.send(res)
            else:
                self.send(f"👁 Now watching trend: <b>{text[7:].strip()}</b>")
        else:
            self.send("❓ Unknown command. Send /help for options.", self.get_main_menu())

    def _cmd_help(self):
        msg = (
            "🧙 <b>SORCERER Commands</b>\n\n"
            "<b>Quick Setup</b>\n"
            "/setup — Load preset niche channels\n"
            "/full — Load ALL channels (15+ signals)\n\n"
            "<b>YouTube Radar</b>\n"
            "/add @channel — Add a channel\n"
            "/remove name — Stop watching\n"
            "/list — See all channels monitored\n"
            "/scan — Run a full scan right now\n\n"
            "<b>Google Trends</b>\n"
            "/watch keyword — Monitor a topic\n"
            "/trends — See all active keywords\n\n"
            "<b>Reporting & Info</b>\n"
            "/status — Operational health report\n"
            "/usage — Token usage and cost report\n"
            "/help — Show this message\n\n"
            "<i>Assets for your response videos (in each alert):</i>\n"
            "• Word-for-word voiceover scripts\n"
            "• Thumbnail concepts & visual hooks"
        )
        self.send(msg, self.get_main_menu())

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
                    # Send progress every 10 channels
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

    def _cmd_voice_menu(self):
        if not self.focus_video:
            self.send("❌ <b>No target video.</b>\nInteract with a signal alert first or add a channel.")
            return
        
        msg = (
            f"🎙 <b>Response Script Generator</b>\n"
            f"Target: <i>{self.focus_video['title']}</i>\n\n"
            f"Choose your response duration:"
        )
        markup = {
            "keyboard": [
                ["/resp_short (2m 50s)", "/resp_med (6m)"],
                ["/resp_long (15m)", "/help"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        self.send(msg, markup)

    def _cmd_screen(self):
        if not self.focus_video:
            self.send("❌ <b>No target video.</b>\nWait for a signal alert or run /scan first.")
            return
        
        if not self.screen_fn:
            self.send("❌ Screen asset generator not configured.")
            return
        
        self.send("🔍 <b>Analyzing video for key visual moments...</b>\n<i>Identifying the best frames to screenshot and crop for your response. ~30 sec</i>")
        
        def run():
            try:
                result = self.screen_fn(self.focus_video)
                self.send(result, self.get_main_menu())
            except Exception as e:
                self.send(f"❌ Error: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def _generate_resp(self, length):
        if not self.script_fn or not self.focus_video:
            self.send("❌ Cannot generate script right now.")
            return
        
        self.send(f"✍ <b>Generating {length.replace('resp_', '')} response script...</b>\nThis may take 30-60 seconds.")
        
        def run():
            try:
                res = self.script_fn(self.focus_video, length)
                # Script function should return the formatted script string
                if res:
                    self.send(res, self.get_main_menu())
                else:
                    self.send("❌ Script generation failed.")
            except Exception as e:
                self.send(f"❌ Error: {e}")
        
        threading.Thread(target=run, daemon=True).start()
