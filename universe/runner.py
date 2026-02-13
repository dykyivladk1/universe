"""Runs an agent or a team and turns the LangGraph stream into simple events for the UI.

Events look like:
    {"type": "agent", "agent": "coder", "name": "Coder"}   # someone starts talking
    {"type": "token", "text": "..."}
    {"type": "tool", "tool": "calculator"}                 # agent is using a tool
"""
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage

from universe.agents import build_agent, to_lc_messages
from universe.orchestrator import build_team


def _chunk_text(chunk):
    # anthropic sends content as list of blocks, openai as a string.
    # .text handles both
    try:
        return chunk.text
    except Exception:
        return chunk.content if isinstance(chunk.content, str) else ""


def _stream_graph(graph, inputs, names):
    current = None

    # subgraphs=True is needed for teams, otherwise tokens from the agents
    # running inside the team nodes are not streamed at all
    for namespace, mode, payload in graph.stream(
        inputs, stream_mode=["messages", "updates"], subgraphs=True
    ):
        if mode == "updates":
            if namespace:
                continue  # updates from inside an agent, we don't care
            # supervisor decided who is next -> tell the UI before tokens arrive
            sup = payload.get("supervisor") if isinstance(payload, dict) else None
            if sup and sup.get("next") in names and sup["next"] != current:
                current = sup["next"]
                yield {"type": "agent", "agent": current, "name": names[current]}
            continue

        msg, meta = payload
        if "router" in (meta.get("tags") or []):
            continue

        if isinstance(msg, ToolMessage):
            yield {"type": "tool", "tool": msg.name}
        elif isinstance(msg, AIMessageChunk):
            text = _chunk_text(msg)
            if text:
                yield {"type": "token", "text": text}


def run(kind, target_id, spec, history, message, agent_specs=None):
    """kind is 'agent' or 'team'. history is our json list, without the new message."""
    messages = to_lc_messages(history) + [HumanMessage(message)]

    if kind == "agent":
        graph = build_agent(target_id, spec)
        yield {"type": "agent", "agent": target_id, "name": spec["name"]}
        yield from _stream_graph(graph, {"messages": messages}, {target_id: spec["name"]})
        return

    graph = build_team(spec, agent_specs)
    names = {a: s["name"] for a, s in agent_specs.items()}
    yield from _stream_graph(graph, {"messages": messages, "steps": 0}, names)
