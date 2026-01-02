import json

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from universe.llms import get_llm
from universe.tools import get_tools

# compiled agents are cheap-ish but not free, so keep them around.
# key includes the whole spec so editing an agent gives a fresh build
_cache = {}


def build_agent(agent_id, spec):
    key = agent_id + json.dumps(spec, sort_keys=True, default=str)
    if key in _cache:
        return _cache[key]

    agent = create_agent(
        model=get_llm(spec["model"], spec.get("temperature", 0.7)),
        tools=get_tools(spec.get("tools", [])),
        system_prompt=spec.get("system_prompt") or None,
        name=agent_id,
    )
    _cache[key] = agent
    return agent


