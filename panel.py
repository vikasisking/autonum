# panel.py

import re
import requests
from config import BASE, USERNAME, PASSWORD, PAGE_LENGTH

LOGIN_PAGE = f"{BASE}/login"
LOGIN_POST = f"{BASE}/signin"
SEARCH_API = f"{BASE}/agent/res/data_smsnumbers2.php"

session = requests.Session()


def solve_captcha(html: str) -> str:
    match = re.search(r"(\d+)\s*\+\s*(\d+)", html)
    if not match:
        raise Exception("❌ Captcha not found in page.")
    a, b = int(match.group(1)), int(match.group(2))
    print(f"🧠 Captcha: {a} + {b} = {a + b}")
    return str(a + b)


def login() -> bool:
    print("🔁 Connecting to panel...")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE}/"
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


def extract_id_from_checkbox(html_cell: str) -> str:
    m = re.search(r"value=['\"](\d+)['\"]", html_cell)
    return m.group(1) if m else ""


def fetch_all_numbers() -> dict:
    """
    MySMSNumbers2 se saare numbers fetch karega (pagination ke sath)
    Return: dict { number: {...info...} }
    """
    print("📥 Fetching all numbers from panel...")
    all_rows = []
    start = 0

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
            "iDisplayLength": str(PAGE_LENGTH),
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

        if len(rows) < PAGE_LENGTH:
            break
        start += PAGE_LENGTH

    numbers: dict[str, dict] = {}
    for row in all_rows:
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
                "limits": limits,
            }
        except Exception:
            continue

    print(f"✅ Total numbers fetched: {len(numbers)}")
    return numbers
