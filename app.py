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
