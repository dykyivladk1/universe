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


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "agent"


# ---------------- agents + teams ----------------

def _default_agents():
    return {
        "agents": {
            "coder": {
                "name": "Coder",
                "description": "Coding help, short answers.",
                "model": "gpt-4.1",
                "system_prompt": (
                    "You are an AI coding assistant. You are really good at programming "
                    "and can help with basically anything the user asks.\n"
                    "Answer short unless the user asks for a long answer."
                ),
                "tools": [],
                "created_at": now(),
            },
            "analyst": {
                "name": "Analyst",
                "description": "Does math with a calculator and reads links.",
                "model": "claude-sonnet-4-5",
                "system_prompt": (
                    "You are a careful analyst. Use the calculator for any math, "
                    "and fetch_url when the user gives you a link. Be concise."
                ),
                "tools": ["calculator", "current_datetime", "fetch_url"],
                "created_at": now(),
            },
        },
        "teams": {
            "dev-team": {
                "name": "Dev Team",
                "description": "Coder and Analyst, a supervisor picks who answers.",
                "router_model": "gpt-4.1-mini",
                "members": ["coder", "analyst"],
                "created_at": now(),
            }
        },
    }


