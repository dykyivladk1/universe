import json

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from universe.llms import get_llm
from universe.tools import get_tools

# compiled agents are cheap-ish but not free, so keep them around.
# key includes the whole spec so editing an agent gives a fresh build
_cache = {}


