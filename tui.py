import os
import re
import sys
import psutil
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from utils import get_weather, get_prayer_times, get_today_schedule, ask_groq, ask_local


# ── helpers ──────────────────────────────────────────────────────────────────
def bar(pct, width=12):
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

def strip_emoji(text):
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()

def compact_weather(raw):
    lines = [strip_emoji(l).strip() for l in raw.splitlines() if strip_emoji(l).strip()]
    return "  ".join(lines[:4]) if lines else "error"

def compact_prayer(raw):
    lines = [strip_emoji(l).strip() for l in raw.splitlines() if strip_emoji(l).strip()]
    for l in lines:
        if "Fajr" in l:
            return l
    return strip_emoji(raw)

def compact_schedule(raw):
    lines = [strip_emoji(l).strip() for l in raw.splitlines() if strip_emoji(l).strip()]
    out = [l for l in lines if l and "Schedule" not in l and "Today" not in l]
    return "  |  ".join(out[:4]) if out else "no events today"

# ── state ─────────────────────────────────────────────────────────────────────
state = {
    "cpu": 0.0, "ram": 0.0, "disk": 0.0,
    "net_sent": 0.0, "net_recv": 0.0,
    "weather": "loading...",
    "prayer": "loading...",
    "schedule": "loading...",
    "chat": [],
    "thinking": False,
}

dirty = threading.Event()

# ── background threads ────────────────────────────────────────────────────────
def refresh_stats():
    while True:
        state["cpu"]      = psutil.cpu_percent(interval=2)
        state["ram"]      = psutil.virtual_memory().percent
        state["disk"]     = psutil.disk_usage("/").percent
        net               = psutil.net_io_counters()
        state["net_sent"] = round(net.bytes_sent / (1024**2), 1)
        state["net_recv"] = round(net.bytes_recv / (1024**2), 1)
        dirty.set()
        time.sleep(5)

def refresh_info():
    while True:
        try:    state["weather"]  = compact_weather(get_weather())
        except: state["weather"]  = "error"
        try:    state["prayer"]   = compact_prayer(get_prayer_times())
        except: state["prayer"]   = "error"
        try:    state["schedule"] = compact_schedule(get_today_schedule())
        except: state["schedule"] = "error"
        dirty.set()
        time.sleep(300)

# ── colors ────────────────────────────────────────────────────────────────────
G  = "\033[32m"
BG = "\033[92m"
DM = "\033[2m"
W  = "\033[97m"
RS = "\033[0m"
CL = "\033[2J\033[H"
SEP_W = 66

# ── render ────────────────────────────────────────────────────────────────────
def draw():
    now  = datetime.now().strftime("%H:%M:%S")
    date = datetime.now().strftime("%a %d %b %Y").upper()
    sep  = f"  {DM}{G}" + "─" * SEP_W + RS

    out = [CL, ""]
    out.append(f"  {BG}PAIDEIA{RS} {DM}{G}//{RS} {G}PN41{RS} {DM}{G}//{RS} {G}{now}  {date}{RS}")
    out.append(sep)

    cb = bar(state["cpu"])
    rb = bar(state["ram"])
    db = bar(state["disk"])

    out.append(f"  {DM}{G}SYS{RS}   {DM}{G}cpu{RS} {BG}{cb}{RS} {G}{state['cpu']:5.1f}%{RS}   {DM}{G}ram{RS} {BG}{rb}{RS} {G}{state['ram']:5.1f}%{RS}")
    out.append(f"  {DM}{G}DSK{RS}   {BG}{db}{RS} {G}{state['disk']:5.1f}%{RS}")
    out.append(f"  {DM}{G}NET{RS}   {G}up {state['net_sent']} mb   dn {state['net_recv']} mb{RS}")
    out.append(sep)
    out.append(f"  {DM}{G}WTHR{RS}  {G}{state['weather']}{RS}")
    out.append(f"  {DM}{G}PRAY{RS}  {G}{state['prayer']}{RS}")
    out.append(f"  {DM}{G}SCHD{RS}  {G}{state['schedule']}{RS}")
    out.append(sep)

    chat = state["chat"][-8:]
    if not chat and not state["thinking"]:
        out.append(f"  {DM}{G}AI    Welcome Affan. type below to chat.{RS}")
    for who, msg in chat:
        if who == "you":
            out.append(f"  {DM}{G}YOU{RS}   {W}{msg}{RS}")
        else:
            out.append(f"  {DM}{G}AI{RS}    {G}{msg}{RS}")
    if state["thinking"]:
        out.append(f"  {DM}{G}AI    thinking...{RS}")

    out.append(sep)
    out.append(f"  {DM}{G}[q] quit   [r] refresh   [c] clear chat   [L] ask terra: {RS}")
    out.append("")
    out.append(f"  {BG}>{RS} ")

    sys.stdout.write("\n".join(out))
    sys.stdout.flush()

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    threading.Thread(target=refresh_stats, daemon=True).start()
    threading.Thread(target=refresh_info,  daemon=True).start()

    def redraw_loop():
        while True:
            dirty.wait()
            dirty.clear()
            draw()

    threading.Thread(target=redraw_loop, daemon=True).start()

    draw()

    while True:
        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.lower() == "q":
            break
        elif user_input.lower() == "r":
            state["weather"] = state["prayer"] = state["schedule"] = "refreshing..."
            threading.Thread(target=refresh_info, daemon=True).start()
            dirty.set()
        elif user_input.lower() == "c":
            state["chat"] = []
            dirty.set()
        elif user_input.lower() == "L:":
            state["chat"].append(("ai", "hint: prefix message with 'l:' to use local model"))
            dirty.set()
        elif not user_input:
            dirty.set()
        else:
            state["chat"].append(("you", user_input))
            state["thinking"] = True
            dirty.set()

            def ask(msg):
                if msg.lower().startswith("l:"):
                    query = msg[2:].strip()
                    tag = "[Terra]"
                    reply = ask_local(query)
                else:
                    tag = "[Aether]"
                    reply = ask_groq(msg)
                words = reply.split()
                line, chunks = [], []
                for word in words:
                    line.append(word)
                    if len(" ".join(line)) > 55:
                        chunks.append(" ".join(line))
                        line = []
                if line:
                    chunks.append(" ".join(line))
                state["chat"].append(("ai", f"{tag}"))
                for chunk in chunks:
                    state["chat"].append(("ai", chunk))
                state["thinking"] = False
                dirty.set()

            threading.Thread(target=ask, args=(user_input,), daemon=True).start()

    sys.stdout.write("\033[2J\033[H")
    print(f"\n  {DM}{G}paideia offline. goodbye affan.{RS}\n")


if __name__ == "__main__":
    main()