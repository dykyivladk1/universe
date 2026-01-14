"""Team orchestration with LangGraph.

A team is a supervisor (router LLM) + a few agents. The flow is:

    START -> supervisor -> some agent -> supervisor -> ... -> FINISH -> END

The supervisor looks at the conversation and picks who should talk next,
or FINISH when the user got what they asked for.
"""
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field, create_model

from universe import config
from universe.agents import build_agent
from universe.llms import get_llm

ROUTER_PROMPT = """You are the supervisor of a small team of AI agents.
Your job is only to decide who should act next, you never answer the user yourself.

Team members:
{members}

Rules:
- Pick the member that fits the latest user request best.
- If a member already answered the request fully, answer FINISH.
- Don't send the same member twice in a row unless it's really needed.
- When in doubt, FINISH. The user can always ask a follow-up."""


class TeamState(MessagesState):
    next: str
    steps: int


