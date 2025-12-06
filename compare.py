# compare.py

from datetime import datetime
from pathlib import Path
import requests
from config import TELEGRAM_BOT_TOKEN, GROUP_CHAT_ID
from cache_store import load_cache, save_cache
from file_map import load_file_map, save_file_map


# ===== COUNTRY FLAGS (add more if needed) =====
FLAG = {
    "Nigeria": "🇳🇬",
    "Comoros": "🇰🇲",
    "India": "🇮🇳",
    "Venezuela": "🇻🇪",
    "Mexico": "🇲🇽",
    "USA": "🇺🇸",
    "Colombia": "🇨🇴",
    "Pakistan": "🇵🇰",
    "Brazil": "🇧🇷",
    "Indonesia": "🇮🇩",
    "Turkey": "🇹🇷",
}

def tg(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": GROUP_CHAT_ID, "text": msg, "parse_mode": "HTML"},
    )


def send_file(path, caption):
    with open(path, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
            data={"chat_id": GROUP_CHAT_ID, "caption": caption},
            files={"document": f},
        )


def export(country, numbers, prefix=""):
    """Creates and sends txt export"""
    Path("exports").mkdir(exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_id = now[-5:]
    short = country[:2].upper()
    name = f"exports/{prefix}{country}_{short}-{file_id}.txt"

    with open(name, "w") as f:
        f.write("\n".join(numbers))

    flag = FLAG.get(country, "🌍")
    caption = (
        f"{flag} {country} | WP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 TOTAL :: {len(numbers)} numbers\n"
        f"🧾 FILE ID :: {short}-{file_id}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    send_file(name, caption)
    print("📁 Export sent:", name)


def compare_states(old, new):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    old_nums = set(old.keys())
    new_nums = set(new.keys())

    added = new_nums - old_nums
    removed = old_nums - new_nums
    common = old_nums & new_nums

    # ===================== ADDED =====================
    if added:
        country_map = {}

        for num in added:
            country = new[num]["range"].split("-")[0].strip()
            new[num]["added"] = now
            country_map.setdefault(country, [])
            country_map[country].append(num)

        msg = f"🆕 <b>{len(added)} Numbers Added</b>\n📅 {now}\n"
        msg += "🌍 " + ", ".join(f"{c}({len(v)})" for c, v in country_map.items())
        tg(msg)

        for country, nums in country_map.items():
            export(country, nums)

    # ===================== REMOVED =====================
    if removed:
        file_map = load_file_map()
        country_map = {}

        for num in removed:
            country = old[num]["range"].split("-")[0].strip()
            country_map.setdefault(country, [])
            country_map[country].append(num)

            for fname, fdata in file_map.items():
                if num in fdata["numbers"] and fdata["status"] == "ACTIVE":
                    fdata["numbers"] = [x for x in fdata["numbers"] if x not in removed]

                    if len(fdata["numbers"]) < 500:
                        fdata["status"] = "DISCONNECTED"
                        fdata["disconnected_on"] = now
                        save_file_map(file_map)

                        # Export OLD updated file
                        export(country, fdata["numbers"], prefix="OLD_")

        msg = f"❌ <b>{len(removed)} Numbers Removed</b>\n📅 {now}\n"
        msg += "🌍 " + ", ".join(f"{c}({len(v)})" for c, v in country_map.items())
        tg(msg)

    # ===================== UPDATED =====================
    updates = []
    for num in common:
        if old[num]["payout"] != new[num]["payout"] or old[num]["limits"] != new[num]["limits"]:
            updates.append(num)

    if updates:
        tg(f"⚡ <b>{len(updates)} Numbers Updated</b>\n📅 {now}")

    # ===== CLEANUP added key before caching =====
    for num in new:
        new[num].pop("added", None)

    save_cache(new)
