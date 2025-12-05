# compare.py

from datetime import datetime
from pathlib import Path

from telegram_util import send_telegram, send_document
from file_map import load_file_map, save_file_map


def compare_states(old, new):
    """
    old, new: dicts keyed by number, contains:
        range, payout, limits, added(optional)
    Features:
      - Detect added numbers
      - Detect removed numbers
      - Disconnect TXT files if any number removed
      - Rebuild updated TXT files after removal
      - Auto-export per-country TXT for added numbers
    """

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    old_nums = set(old.keys())
    new_nums = set(new.keys())

    added = new_nums - old_nums
    removed = old_nums - new_nums
    common = new_nums & old_nums

    # ================================================
    #            ADDED NUMBERS HANDLING
    # ================================================
    if added:
        country_map = {}  # country → [numbers]
        for num in added:
            info = new[num]
            country = info["range"].split("-")[0].strip()
            country_map.setdefault(country, []).append(num)
            new[num]["added"] = now  # save time

        # Summary alert
        msg = (
            f"🆕 <b>{len(added)} Numbers Added</b>\n"
            f"🌍 Countries: {', '.join(f'{c}({len(country_map[c])})' for c in country_map)}\n"
            f"📅 Added On: {now}"
        )
        print(msg)
        send_telegram(msg)

        # Export TXT per country
        from pathlib import Path
        Path("added_exports").mkdir(exist_ok=True)

        # flag mapping
        flag_map = {
            "Venezuela": "🇻🇪",
            "India": "🇮🇳",
            "USA": "🇺🇸",
            "Mexico": "🇲🇽",
            "Colombia": "🇨🇴",
            "Brazil": "🇧🇷",
            "Pakistan": "🇵🇰",
            "Nigeria": "🇳🇬",
            "Indonesia": "🇮🇩",
            "Turkey": "🇹🇷",
        }

        for country, nums in country_map.items():
            safe_time = now.replace(":", "-").replace(" ", "_")
            fid = str(abs(hash(country + now)))[:5]
            file_name = f"added_exports/{country}_{fid}.txt"

            with open(file_name, "w") as f:
                f.write("\n".join(nums))

            flag = flag_map.get(country, "🌍")
            caption = (
                f"{flag} {country} | WP\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 TOTAL :: {len(nums)} numbers\n"
                f"🧾 FILE ID :: {country[:2].upper()}-{fid}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )

            # send document
            with open(file_name, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                    data={"chat_id": GROUP_CHAT_ID, "caption": caption},
                    files={"document": f}
                )

    # ================================================
    #              REMOVED NUMBERS HANDLING
    # ================================================
    if removed:
        file_map = load_file_map()
        affected_files = set()

        # Which files affected?
        for num in removed:
            for fname, fdata in file_map.items():
                if num in fdata["numbers"] and fdata["status"] == "ACTIVE":
                    affected_files.add(fname)

        # alert
        msg = (
            f"❌ <b>{len(removed)} Numbers Removed</b>\n"
            f"📅 Time: {now}"
        )
        print(msg)
        send_telegram(msg)

        # If no file affected no rebuild
        if affected_files:
            from pathlib import Path
            Path("updated_exports").mkdir(exist_ok=True)

            for fname in affected_files:
                fdata = file_map[fname]
                original_numbers = fdata["numbers"]

                # remaining numbers after removal
                remaining = [n for n in original_numbers if n not in removed]
                removed_count = len(original_numbers) - len(remaining)

                # archive file
                fdata["status"] = "ARCHIVED"
                fdata["archived_on"] = now

                if remaining:
                    new_file = f"updated_exports/{fname.replace('.txt','')}_OLD_{now.replace(' ','_').replace(':','-')}.txt"
                    with open(new_file, "w") as f:
                        f.write("\n".join(remaining))

                    old_count = len(original_numbers)
                    new_count = len(remaining)

                    caption = (
                        f"📁 <b>FILE UPDATED (OLD REMOVED)</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📦 OLD TOTAL :: {old_count}\n"
                        f"❌ REMOVED :: {removed_count}\n"
                        f"📦 NEW TOTAL :: {new_count}\n"
                        f"🧾 FILE :: {fname}\n"
                        f"📅 Time :: {now}\n"
                        f"━━━━━━━━━━━━━━━━━━"
                    )

                    with open(new_file, "rb") as f:
                        requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                            data={"chat_id": GROUP_CHAT_ID, "caption": caption},
                            files={"document": f}
                        )
                # If remaining == 0 → no new file

            save_file_map(file_map)

    # ================================================
    #                UPDATED NUMBERS
    # ================================================
    changes = []
    for num in common:
        if old[num].get("payout") != new[num].get("payout") or old[num].get("limits") != new[num].get("limits"):
            changes.append(num)

    if changes:
        msg = (
            f"⚡ <b>{len(changes)} Numbers Updated</b>\n"
            f"📅 Checked At: {now}"
        )
        print(msg)
        send_telegram(msg)
