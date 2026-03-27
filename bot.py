#!/usr/bin/env python3
"""
SORCERER Telegram Bot — Remote control for the YouTube intelligence agent.
Runs in background thread. Supports /help, /scan, /add, /list, /status commands.
"""

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
        
        # Functions that will be injected by the caller
        self.scan_fn = None
        self.add_fn = None
        
        self.offset = 0
    
    def send(self, message):
        """Send a message to the configured chat."""
        try:
            requests.post(
                f"{self.api_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:
            self.log_fn(f"  ⚠  Telegram send error: {e}")
    
    def start_in_background(self):
        """Start the bot polling in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the bot."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _poll_loop(self):
        """Main polling loop — runs in background thread."""
        while self.running:
            try:
                self._fetch_and_handle_updates()
            except Exception as e:
                self.log_fn(f"  ⚠  Bot polling error: {e}")
            
            time.sleep(1)  # Poll every second    
    def _fetch_and_handle_updates(self):
        """Fetch new messages and dispatch to handlers."""
        try:
            resp = requests.get(
                f"{self.api_url}/getUpdates",
                params={"offset": self.offset, "timeout": 10},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("ok"):
                return
            
            for update in data.get("result", []):
                self.offset = update["update_id"] + 1
                
                msg = update.get("message", {})
                if not msg:
                    continue
                
                text = msg.get("text", "").strip()
                if not text:
                    continue
                
                self._handle_message(text)
        
        except requests.Timeout:
            pass
        except Exception as e:
            self.log_fn(f"  ⚠  Update fetch error: {e}")
    
    def _handle_message(self, text):
        """Route incoming commands."""
        if text == "/help":
            self._cmd_help()
        elif text == "/scan":
            self._cmd_scan()
        elif text == "/list":
            self._cmd_list()
        elif text == "/status":
            self._cmd_status()
        elif text.startswith("/add "):
            query = text[5:].strip()
            self._cmd_add(query)
        elif text.startswith("/add@"):  # Handle /add@channel format
            query = text[5:].strip()
            self._cmd_add(query)
        else:
            self.send("❓ Unknown command. Send /help for options.")
    
    def _cmd_help(self):
        """Show help."""
        msg = (
            "🧙 <b>SORCERER Commands</b>\n\n"
            "/scan — Run a full scan right now\n"
            "/list — Show all monitored channels\n"
            "/status — See scan history + recent alerts\n"
            "/add @channel — Start watching a channel\n"
            "/help — Show this message\n\n"
            "<i>Examples:</i>\n"
            "/add @mkbhd\n"
            "/add veritasium\n"
            "/add UCxxxxx (channel ID)\n"
        )
        self.send(msg)
    
    def _cmd_scan(self):
        """Trigger an immediate scan."""
        if not self.scan_fn:
            self.send("❌ Scan function not configured.")
            return
        
        self.send("📡 Scanning all channels... (this may take a moment)")
        
        try:
            new_alerts = self.scan_fn()
            if new_alerts > 0:
                self.send(f"✅ Scan done — {new_alerts} new signal(s) detected!")
            else:
                self.send("✅ Scan done — all quiet.")
        except Exception as e:
            self.send(f"❌ Scan error: {e}")
    
    def _cmd_list(self):
        """List monitored channels."""
        try:
            db = json.loads(self.db_file.read_text())
            channels = db.get("channels", {})
            
            if not channels:
                self.send("📭 No channels monitored yet.\nUse /add @channel to start.")
                return
            
            msg = f"📡 <b>SORCERER RADAR — {len(channels)} channel(s)</b>\n\n"
            
            for ch in list(channels.values())[:10]:  # Limit to 10 for message size
                title = ch.get("title", "Unknown")[:30]
                subs = ch.get("subscribers", 0)
                alerts = ch.get("alert_count", 0)
                msg += f"<b>{title}</b>\n  {subs:,} subs · {alerts} alerts\n\n"
            
            if len(channels) > 10:
                msg += f"<i>... and {len(channels) - 10} more</i>"
            
            self.send(msg)
        except Exception as e:
            self.send(f"❌ Error: {e}")
    
    def _cmd_status(self):
        """Show scan history and recent alerts."""
        try:
            db = json.loads(self.db_file.read_text())
            
            last_scan = db.get("last_scan")
            total_scans = db.get("scans", 0)
            total_alerts = db.get("total_alerts", 0)
            channels = len(db.get("channels", {}))
            
            msg = "<b>📊 SORCERER STATUS</b>\n\n"
            
            if last_scan:
                ago = datetime.now() - datetime.fromisoformat(last_scan)
                h, m = int(ago.total_seconds() / 3600), int((ago.total_seconds() % 3600) / 60)
                msg += f"Last scan: <b>{h}h {m}m ago</b>\n"
            else:
                msg += "Last scan: never\n"
            
            msg += f"Total scans: <b>{total_scans}</b>\n"
            msg += f"Total alerts: <b>{total_alerts}</b>\n"
            msg += f"Channels monitored: <b>{channels}</b>\n"
            
            self.send(msg)
        except Exception as e:
            self.send(f"❌ Error: {e}")
    
    def _cmd_add(self, query):
        """Add a channel to monitor."""
        if not self.add_fn:
            self.send("❌ Add function not configured.")
            return
        
        self.send(f"🔍 Looking up: {query}...")
        
        try:
            result = self.add_fn(query)
            self.send(result)
        except Exception as e:
            self.send(f"❌ Error: {e}")
