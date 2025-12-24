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


class AgentStore:
    def __init__(self, path=None):
        self.path = path or config.AGENTS_FILE
        self.data = _read_json(self.path, None)
        if not self.data:
            self.data = _default_agents()
            self.save()

    def save(self):
        with _lock:
            _write_json(self.path, self.data)

    def _unique_id(self, bucket, name):
        base = slugify(name)
        new_id, i = base, 2
        # "supervisor" is taken by the team graph node
        while new_id in self.data[bucket] or new_id == "supervisor":
            new_id = f"{base}-{i}"
            i += 1
        return new_id

    # agents
    def agents(self):
        return self.data["agents"]

    def get_agent(self, agent_id):
        return self.data["agents"].get(agent_id)

    def save_agent(self, payload, agent_id=None):
        agent_id = agent_id or self._unique_id("agents", payload["name"])
        old = self.data["agents"].get(agent_id, {})
        self.data["agents"][agent_id] = {
            "name": payload["name"],
            "description": payload.get("description", ""),
            "model": payload["model"],
            "temperature": float(payload.get("temperature", 0.7)),
            "system_prompt": payload.get("system_prompt", ""),
            "tools": payload.get("tools", []),
            "created_at": old.get("created_at", now()),
            "updated_at": now(),
        }
        self.save()
        return agent_id

    def duplicate_agent(self, agent_id):
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        copy = dict(agent, name=agent["name"] + " (copy)")
        return self.save_agent(copy)

    def delete_agent(self, agent_id):
        self.data["agents"].pop(agent_id, None)
        # also kick it out of any team it was in
        for team in self.data["teams"].values():
            if agent_id in team["members"]:
                team["members"].remove(agent_id)
        self.save()

    # teams
    def teams(self):
        return self.data["teams"]

    def get_team(self, team_id):
        return self.data["teams"].get(team_id)

    def save_team(self, payload, team_id=None):
        team_id = team_id or self._unique_id("teams", payload["name"])
        old = self.data["teams"].get(team_id, {})
        self.data["teams"][team_id] = {
            "name": payload["name"],
            "description": payload.get("description", ""),
            "router_model": payload["router_model"],
            "members": payload["members"],
            "created_at": old.get("created_at", now()),
            "updated_at": now(),
        }
        self.save()
        return team_id

    def delete_team(self, team_id):
        self.data["teams"].pop(team_id, None)
        self.save()


# ---------------- chat history ----------------
# same shape as the old history/chat_histories.json:
# { user_id: { chat_id: {title, messages: [{role, content}], created_at} } }

class ChatStore:
    def __init__(self, path=None):
        self.path = path or config.CHATS_FILE
        self.data = _read_json(self.path, {})

    def save(self):
        with _lock:
            _write_json(self.path, self.data)

    def get_chat(self, user_id, chat_id, create=True):
        user_chats = self.data.setdefault(user_id, {})
        if chat_id not in user_chats and create:
            user_chats[chat_id] = {"title": "Chat", "messages": [], "created_at": now()}
        return user_chats.get(chat_id)

    def add_message(self, user_id, chat_id, role, content, agent=None):
        chat = self.get_chat(user_id, chat_id)
        msg = {"role": role, "content": content}
        if agent:
            msg["agent"] = agent
        chat["messages"].append(msg)

        if chat["title"] == "Chat" and role == "user" and content:
            chat["title"] = content[:30] + ("..." if len(content) > 30 else "")
        self.save()

    def clear(self, user_id, chat_id):
        chat = self.get_chat(user_id, chat_id, create=False)
        if chat:
            chat["messages"] = []
            self.save()

    def delete(self, user_id, chat_id):
        self.data.get(user_id, {}).pop(chat_id, None)
        self.save()
