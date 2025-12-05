# file_map.py

import json
from pathlib import Path
from datetime import datetime

FILE_MAP = Path("file_map.json")


def load_file_map():
    if not FILE_MAP.exists():
        return {}
    try:
        with open(FILE_MAP, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_file_map(data: dict):
    with open(FILE_MAP, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_file(file_name: str, numbers: list[str]):
    """
    TXT file ko register karega:
    - numbers: list of strings
    - status: ACTIVE / DISCONNECTED
    """
    data = load_file_map()
    data[file_name] = {
        "numbers": numbers,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "ACTIVE"
    }
    save_file_map(data)
    print(f"📁 File registered: {file_name} (numbers: {len(numbers)})")
