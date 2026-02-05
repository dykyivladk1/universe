"""Runs an agent or a team and turns the LangGraph stream into simple events for the UI.

Events look like:
    {"type": "agent", "agent": "coder", "name": "Coder"}   # someone starts talking
    {"type": "token", "text": "..."}
    {"type": "tool", "tool": "calculator"}                 # agent is using a tool
"""
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage

from universe.agents import build_agent, to_lc_messages
from universe.orchestrator import build_team


