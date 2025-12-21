import json
import re
import threading
from datetime import datetime

from universe import config

_lock = threading.Lock()


def _read_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[WARN] {path.name} is broken, starting from empty")
        return default


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    tmp.replace(path)  # so we never end up with half-written file


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


