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


