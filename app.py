import json
import uuid

from flask import (
    Flask, Response, abort, jsonify, redirect, render_template,
    request, session, stream_with_context, url_for,
)

from universe import config, runner
from universe.llms import MODELS, list_models
from universe.presets import PRESETS, get_preset
from universe.storage import AgentStore, ChatStore
from universe.tools import TOOLS, list_tools

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.json.sort_keys = False  # keep agents in the order they were created

agent_store = AgentStore()
chat_store = ChatStore()


def current_user():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return session["user_id"]


def sse(data):
    return f"data: {json.dumps(data)}\n\n"


@app.template_filter("avatar_color")
def avatar_color(agent_id):
    # same formula as avatarColor() in chat.js, so colors match everywhere
    return f"av-{sum(ord(c) for c in agent_id) % 8}"


@app.template_filter("initials")
def initials(name):
    return "".join(word[0] for word in name.split()[:2]).upper() or "?"


@app.context_processor
def sidebar_data():
    # the sidebar is on every page, so just give every template the lists
    return {"nav_agents": agent_store.agents(), "nav_teams": agent_store.teams()}


def parse_target(target):
    """'agent:coder' -> ('agent', 'coder')"""
    kind, _, target_id = (target or "").partition(":")
    if kind not in ("agent", "team") or not target_id:
        return None, None
    return kind, target_id


# ---------------- pages ----------------

@app.route("/")
def dashboard():
    current_user()
    return render_template("dashboard.html", active="dashboard")


@app.route("/agents/<agent_id>")
def agent_builder(agent_id):
    if not agent_store.get_agent(agent_id):
        abort(404)
    return render_template("builder.html", kind="agent", target_id=agent_id, active=f"agent:{agent_id}")


@app.route("/teams/<team_id>")
def team_builder(team_id):
    if not agent_store.get_team(team_id):
        abort(404)
    return render_template("builder.html", kind="team", target_id=team_id, active=f"team:{team_id}")


@app.route("/c/<path:target>")
def chat_page(target):
    kind, target_id = parse_target(target)
    if not kind:
        return redirect(url_for("dashboard"))
    return render_template("chat.html", target=target, active=target)


# ---------------- config ----------------

@app.route("/api/config")
def get_config():
    return jsonify({
        "models": list_models(),
        "tools": list_tools(),
        "presets": PRESETS,
        "agents": agent_store.agents(),
        "teams": agent_store.teams(),
        "history_limit": config.HISTORY_LIMIT,
    })


# ---------------- agents ----------------

def validate_agent(data):
    if not data.get("name", "").strip():
        return "Name is required"
    if data.get("model") not in MODELS:
        return "Unknown model"
    try:
        temp = float(data.get("temperature", 0.7))
    except (TypeError, ValueError):
        return "Temperature must be a number"
    if not 0 <= temp <= 2:
        return "Temperature must be between 0 and 2"
    bad_tools = [t for t in data.get("tools", []) if t not in TOOLS]
    if bad_tools:
        return f"Unknown tools: {', '.join(bad_tools)}"
    return None


@app.route("/api/agents", methods=["POST"])
@app.route("/api/agents/<agent_id>", methods=["PUT"])
def save_agent(agent_id=None):
    data = request.get_json() or {}

    # creating from a preset: {"preset": "coder"} is enough
    if not agent_id and "preset" in data:
        preset = get_preset(data["preset"])
        data = {**preset, **{k: v for k, v in data.items() if k != "preset"}}
        if preset["key"] == "blank":
            data["name"] = data.get("name") or "New agent"

    error = validate_agent(data)
    if error:
        return jsonify({"error": error}), 400
    if agent_id and not agent_store.get_agent(agent_id):
        return jsonify({"error": "Agent not found"}), 404

    agent_id = agent_store.save_agent(data, agent_id)
    return jsonify({"status": "ok", "id": agent_id, "agent": agent_store.get_agent(agent_id)})


@app.route("/api/agents/<agent_id>/duplicate", methods=["POST"])
def duplicate_agent(agent_id):
    new_id = agent_store.duplicate_agent(agent_id)
    if not new_id:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify({"status": "ok", "id": new_id})


@app.route("/api/agents/<agent_id>", methods=["DELETE"])
def delete_agent(agent_id):
    agent_store.delete_agent(agent_id)
    return jsonify({"status": "ok"})


# ---------------- teams ----------------

@app.route("/api/teams", methods=["POST"])
@app.route("/api/teams/<team_id>", methods=["PUT"])
def save_team(team_id=None):
    data = request.get_json() or {}
    if not data.get("name", "").strip():
        return jsonify({"error": "Name is required"}), 400
    if data.get("router_model") not in MODELS:
        return jsonify({"error": "Unknown router model"}), 400

    members = [m for m in data.get("members", []) if agent_store.get_agent(m)]
    if len(members) < 2:
        return jsonify({"error": "A team needs at least 2 agents"}), 400
    data["members"] = members

    team_id = agent_store.save_team(data, team_id)
    return jsonify({"status": "ok", "id": team_id, "team": agent_store.get_team(team_id)})


@app.route("/api/teams/<team_id>", methods=["DELETE"])
def delete_team(team_id):
    agent_store.delete_team(team_id)
    return jsonify({"status": "ok"})


# ---------------- chat ----------------

@app.route("/chat")
def chat():
    user_id = current_user()
    message = request.args.get("message", "").strip()
    target = request.args.get("target", "")
    kind, target_id = parse_target(target)

    if not message:
        return jsonify({"error": "Empty message"}), 400

    if kind == "agent":
        spec = agent_store.get_agent(target_id)
        member_specs = None
    elif kind == "team":
        spec = agent_store.get_team(target_id)
        member_specs = {a: agent_store.get_agent(a) for a in (spec or {}).get("members", [])}
        member_specs = {a: s for a, s in member_specs.items() if s}
    else:
        spec = None

    if not spec:
        return jsonify({"error": f"Nothing found for {target}"}), 404

    # normal chat uses the target as thread id, the builder playground
    # sends thread=playground:... so testing doesn't mess up the real history
    chat_id = request.args.get("thread") or target
    history = chat_store.get_chat(user_id, chat_id)["messages"][-config.HISTORY_LIMIT:]
    chat_store.add_message(user_id, chat_id, "user", message)

    def generate():
        # one entry per agent turn, so team answers are saved as separate bubbles
        turns = []
        try:
            for event in runner.run(kind, target_id, spec, history, message, member_specs):
                if event["type"] == "agent":
                    turns.append({"agent": event["agent"], "text": ""})
                elif event["type"] == "token":
                    if not turns:
                        turns.append({"agent": None, "text": ""})
                    turns[-1]["text"] += event["text"]
                yield sse({**event, "done": False})

            yield sse({"type": "done", "done": True})

        except Exception as e:
            print(f"[ERROR] {target}: {e}")
            yield sse({"type": "error", "error": str(e), "done": True})

        finally:
            # runs also when the user hits stop and the connection drops,
            # so whatever was generated so far is still saved
            for turn in turns:
                if turn["text"].strip():
                    chat_store.add_message(user_id, chat_id, "assistant", turn["text"], agent=turn["agent"])

    return Response(stream_with_context(generate()), content_type="text/event-stream")


@app.route("/chat/history/<path:chat_id>")
def chat_history(chat_id):
    chat = chat_store.get_chat(current_user(), chat_id, create=False)
    if not chat:
        return jsonify({"status": "success", "chat": {"title": "Chat", "messages": []}})
    return jsonify({"status": "success", "chat": chat})


@app.route("/chat/clear/<path:chat_id>", methods=["POST"])
def clear_chat(chat_id):
    chat_store.clear(current_user(), chat_id)
    return jsonify({"status": "success"})


@app.route("/chat/delete/<path:chat_id>", methods=["POST"])
def delete_chat(chat_id):
    chat_store.delete(current_user(), chat_id)
    return jsonify({"status": "success"})


if __name__ == "__main__":
    if not config.OPENAI_API_KEY and not config.ANTHROPIC_API_KEY:
        print("[WARN] no API keys found, check your .env file")
    app.run(debug=True, host="127.0.0.1", port=config.PORT, threaded=True)
