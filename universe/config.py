import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
AGENTS_FILE = DATA_DIR / "agents.json"
CHATS_FILE = DATA_DIR / "chats.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")

# how many past messages we send back to the model on every turn
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 10))

# a team can bounce between agents, this stops it from looping forever
MAX_TEAM_STEPS = int(os.getenv("MAX_TEAM_STEPS", 6))

PORT = int(os.getenv("PORT", 3000))
