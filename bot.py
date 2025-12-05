import requests
import re
import time
import json
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from telegram.ext import Application, MessageHandler, filters
import threading
from telegram import Update


# ================= PANEL CONFIG =================
BASE = "http://51.89.99.105/NumberPanel"
LOGIN_PAGE = f"{BASE}/login"
LOGIN_POST = f"{BASE}/signin"
SEARCH_API = f"{BASE}/agent/res/data_smsnumbers2.php"

USERNAME = "developer25"
PASSWORD = "developer25"

session = requests.Session()

# ================ TELEGRAM CONFIG (OPTIONAL) ================
# agar Telegram alert chahiye to yaha fill karo
# ================ TELEGRAM CONFIG =================
TELEGRAM_BOT_TOKEN = "8311925389:AAGFWOm8X5Gwzg46AhZf5KckaOkM6O8-LF4"
GROUP_CHAT_ID = "-1003340025073"  # Telegram GROUP ID where bot is admin

def send_telegram(msg: str):
    if not TELEGRAM_BOT_TOKEN or not GROUP_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": GROUP_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"⚠ Telegram send error: {e}")

# ================= CAPTCHA SOLVER =================
def solve_captcha(html):
    match = re.search(r"(\d+)\s*\+\s*(\d+)", html)
    if not match:
        raise Exception("❌ Captcha not found in page.")
    a, b = int(match.group(1)), int(match.group(2))
    print(f"🧠 Captcha: {a} + {b} = {a + b}")
    return str(a + b)

# ================= LOGIN FUNCTION =================
def login() -> bool:
    print("🔁 Connecting to panel...")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://51.89.99.105/NumberPanel/"
    }

    r = session.get(LOGIN_PAGE, headers=headers)
    if r.status_code == 403:
        print("🚫 403 Forbidden - Panel blocked request")
        return False

    captcha_answer = solve_captcha(r.text)

    payload = {"username": USERNAME, "password": PASSWORD, "capt": captcha_answer}
    res = session.post(LOGIN_POST, data=payload, headers=headers)

    if "SMSCDRStats" in res.text:
        print("✅ Login successful!")
        return True

    print("❌ Login failed")
    return False

# ================= FETCH ALL NUMBERS =================
def extract_id_from_checkbox(html_cell: str) -> str:
    # row[0] = "<input type='checkbox' ... value='178151882' />"
    m = re.search(r"value=['\"](\d+)['\"]", html_cell)
    return m.group(1) if m else ""

def fetch_all_numbers():
    """
    MySMSNumbers2 se saare numbers fetch karega (pagination ke sath)
    Return: dict { number: {...info...} }
    """
    print("📥 Fetching all numbers from panel...")
    all_rows = []
    start = 0
    page_len = 50  # ek baar me 50 rows

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE}/agent/MySMSNumbers2"
    }

    while True:
        params = {
            "frange": "",
            "fclient": "",
            "fallocated": "",
            "sEcho": "1",
            "iColumns": "8",
            "sColumns": ",,,,,,,",
            "iDisplayStart": str(start),
            "iDisplayLength": str(page_len),
            "mDataProp_0": "0",
            "mDataProp_1": "1",
            "mDataProp_2": "2",
            "mDataProp_3": "3",
            "mDataProp_4": "4",
            "mDataProp_5": "5",
            "mDataProp_6": "6",
            "mDataProp_7": "7",
            "sSearch": "",
            "bRegex": "false",
            "iSortCol_0": "0",
            "sSortDir_0": "asc",
            "iSortingCols": "1",
        }

        r = session.get(SEARCH_API, params=params, headers=headers)
        try:
            data = r.json()
        except Exception as e:
            print("❌ JSON parse failed while fetching numbers:", e)
            print(r.text[:200])
            break

        rows = data.get("aaData", [])
        if not rows:
            break

        all_rows.extend(rows)
        print(f"  ➕ Loaded {len(rows)} rows (total: {len(all_rows)})")

        if len(rows) < page_len:
            break
        start += page_len

    # convert rows → dict keyed by number
    numbers = {}
    for row in all_rows:
        # expected row format from your test:
        # 0: checkbox html
        # 1: Range
        # 2: Prefix (can be empty)
        # 3: Number
        # 4: Payout (HTML)
        # 5: Allocate link (ignored)
        # 6: empty
        # 7: Limits HTML
        try:
            row_id = extract_id_from_checkbox(row[0])
            rng = row[1]
            prefix = row[2]
            num = row[3]
            payout = row[4]
            limits = row[7]

            if not num:
                continue

            numbers[num] = {
                "id": row_id,
                "range": rng,
                "prefix": prefix,
                "payout": payout,
                "limits": limits
            }
        except Exception:
            continue

    print(f"✅ Total numbers fetched: {len(numbers)}")
    return numbers

def verify_txt(file_path):
    # Load panel cache
    panel = load_cache()
    if not panel:
        print("⚠ Cache empty! Run monitor once before TXT verification.")
        return

    try:
        with open(file_path, "r") as f:
            nums = [i.strip() for i in f.readlines() if i.strip().isdigit()]
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    if not nums:
        print("❌ TXT file has no valid numbers.")
        return

    total = len(nums)

    # Sample selection logic
    samples = []
    samples.append(nums[0])                      # first
    samples.append(nums[total//2])               # middle
    samples.append(nums[-1])                     # last

    if total > 50:
        samples.append(nums[-2])                 # extra sample
        samples.append(nums[-3])

    print(f"🗂 Total numbers in TXT: {total}")
    print(f"🔍 Checking {len(samples)} sample numbers...")

    missing = []

    for num in samples:
        if num not in panel:
            missing.append(num)

    if missing:
        print("❌ TXT verification FAILED!")
        print("Missing numbers (sample):")
        for m in missing:
            print("•", m)

        msg = (
            f"❌ TXT Verification Failed\n"
            f"Missing Sample Count: {len(missing)}\n"
            f"Example Missing: {missing[0]}"
        )
        send_telegram(msg)
    else:
        print("✔ TXT Verified — All sampled numbers exist in panel!")
        msg = (
            f"✔ TXT Verification Success\n"
            f"Total Numbers: {total}\n"
            f"Matched Samples: {len(samples)}"
        )
        send_telegram(msg)

FILE_MAP = "file_map.json"

def load_file_map():
    if not Path(FILE_MAP).exists():
        return {}
    return json.load(open(FILE_MAP))

def save_file_map(data):
    json.dump(data, open(FILE_MAP, "w"), indent=2)

def register_file(file_name, numbers):
    data = load_file_map()
    data[file_name] = {
        "numbers": numbers,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "ACTIVE"
    }
    save_file_map(data)
    print(f"📁 File registered: {file_name}")

def process_txt(file_path):
    """
    Reads TXT, extracts all numbers, and registers file.
    Isko tab call karo jab new TXT approve karni ho.
    """
    try:
        with open(file_path, "r") as f:
            nums = [i.strip() for i in f.readlines() if i.strip().isdigit()]
    except Exception as e:
        print(f"❌ Cannot read file: {e}")
        return

    if not nums:
        print("❌ No valid numbers inside TXT!")
        return

    fname = Path(file_path).name
    register_file(fname, nums)
    print(f"📁 File registered successfully: {fname}")

# ================= CACHE HANDLING =================
CACHE_FILE = Path("panel_cache.json")

def load_cache():
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================= DIFF + ALERT LOGIC =================
def compare_states(old, new):
    """
    old, new: dicts keyed by number, contains:
        range, payout, limits, added(optional)
    Detects:
      - added numbers
      - removed numbers
      - updated numbers
      - file disconnection
      - auto TXT export for added numbers per country
    """

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    old_nums = set(old.keys())
    new_nums = set(new.keys())

    added = new_nums - old_nums
    removed = old_nums - new_nums
    common = new_nums & old_nums

    # ================== ADDED NUMBERS ==================
    if added:
        country_count = {}
        country_map = {}  # country → [numbers list]

        for num in added:
            info = new[num]
            country = info["range"].split("-")[0].strip()
            country_count.setdefault(country, 0)
            country_count[country] += 1

            country_map.setdefault(country, [])
            country_map[country].append(num)

            new[num]["added"] = now  # store timestamp

        msg = (
            f"🆕 <b>{len(added)} Numbers Added</b>\n"
            f"🌍 Countries: {', '.join(f'{c}({country_count[c]})' for c in country_count)}\n"
            f"📅 Added On: {now}"
        )

        print("\n" + msg + "\n")
        send_telegram(msg)

        # ----------- CREATE & SEND COUNTRY TXT FILES -----------
        from pathlib import Path
        Path("added_exports").mkdir(exist_ok=True)

        # Flag mapper (expand later)
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
            file_id = str(abs(hash(country + now)))[:5]
            file_name = f"added_exports/{country}_{safe_time}.txt"

            with open(file_name, "w") as f:
                f.write("\n".join(nums))

            flag = flag_map.get(country, "🌍")
            caption = (
                f"{flag} {country} | WP\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 TOTAL :: {len(nums)} numbers\n"
                f"🧾 FILE ID :: {country[:2].upper()}-{file_id}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )

            try:
                with open(file_name, "rb") as f:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                        data={"chat_id": GROUP_CHAT_ID, "caption": caption},
                        files={"document": f}
                    )
                print(f"📁 TXT Export Sent: {file_name}")
            except Exception as e:
                print("⚠ TXT Upload Failed:", e)

    # ================== REMOVED NUMBERS ==================
    if removed:
        file_map = load_file_map()
        affected_files = set()
        country_count = {}

        for num in removed:
            info = old[num]
            country = info["range"].split("-")[0].strip()
            country_count.setdefault(country, 0)
            country_count[country] += 1

            # Disconnect affected txt files
            for fname, fdata in file_map.items():
                if num in fdata.get("numbers", []) and fdata.get("status") == "ACTIVE":
                    affected_files.add(fname)
                    fdata["status"] = "DISCONNECTED"
                    fdata["disconnected_on"] = now

        msg = (
            f"❌ <b>{len(removed)} Numbers Removed</b>\n"
            f"🌍 Countries: {', '.join(f'{c}({country_count[c]})' for c in country_count)}\n"
            f"📅 Removed On: {now}\n"
        )

        # add info when number was added (example)
        for num in sorted(removed):
            added_time = old[num].get("added", "Unknown")
            msg += f"⏱️ Added At: {added_time}\n"
            break

        print("\n" + msg + "\n")
        send_telegram(msg)

        # If files disconnected
        if affected_files:
            save_file_map(file_map)
            fmsg = (
                "📁 <b>FILE DISCONNECTED!</b>\n"
                f"❌ Reason: Panel numbers removed\n"
                f"Files affected:\n" + "\n".join(f"• {f}" for f in affected_files) +
                f"\n🕒 Time: {now}"
            )
            print("\n" + fmsg + "\n")
            send_telegram(fmsg)

    # ================== UPDATED NUMBERS ==================
    updates = []
    for num in common:
        old_info = old[num]
        new_info = new[num]

        if old_info.get("payout") != new_info.get("payout") or old_info.get("limits") != new_info.get("limits"):
            updates.append(num)

    if updates:
        msg = (
            f"⚡ <b>{len(updates)} Numbers Updated</b>\n"
            f"📅 Checked At: {now}"
        )
        print("\n" + msg + "\n")
        send_telegram(msg)


# ================= TELEGRAM TXT FILE HANDLER =================
# ================= TELEGRAM TXT FILE HANDLER =================
async def handle_txt(update: Update, context):
    if not update.message.document:
        return
    
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        return

    file_name = doc.file_name
    print(f"📁 TXT Received: {file_name}")

    # Download file
    file = await doc.get_file()
    Path("uploads").mkdir(exist_ok=True)
    file_path = f"uploads/{file_name}"
    await file.download_to_drive(file_path)

    # Register TXT numbers into file_map.json
    process_txt(file_path)

    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=f"📁 File Registered: {file_name}\n"
             f"🔍 Monitoring enabled...\n"
             f"🕒 Next panel check in 5 minutes."
    )


# ================= MONITOR LOOP (EVERY 5 MIN) =================
def monitor_loop():
    print("🚀 Starting Auto Monitor System (interval: 5 minutes)\n")

    # initial load
    if not login():
        print("❌ Cannot login, exiting.")
        return

    # first fetch
    current_state = fetch_all_numbers()
    save_cache(current_state)
    print("💾 Initial state saved to panel_cache.json\n")

    while True:
        try:
            print("\n⏳ Waiting 5 minutes before next check...\n")
            time.sleep(300)  # 5 minutes

            # try fetch, if fails due to login → relogin
            try:
                new_state = fetch_all_numbers()
            except Exception as e:
                print(f"⚠ Error fetching numbers: {e}")
                print("🔁 Trying to re-login...")
                if login():
                    new_state = fetch_all_numbers()
                else:
                    print("❌ Re-login failed, skipping this cycle.")
                    continue

            old_state = load_cache()
            compare_states(old_state, new_state)
            save_cache(new_state)

        except KeyboardInterrupt:
            print("🛑 Monitor stopped by user.")
            break
        except Exception as e:
            print(f"❌ Unexpected error in monitor loop: {e}")
            time.sleep(30)

# ================= MAIN STARTER =================
if __name__ == "__main__":
    # 🔁 Start monitor loop in background
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()

    # 🤖 Start Telegram bot listener
    print("🤖 Telegram listener active... waiting for TXT uploads")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_txt))
    app.run_polling(close_loop=False)
