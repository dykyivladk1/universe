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


def _describe(agent_id, spec):
    # first line of the prompt is usually enough for routing
    first_line = (spec.get("system_prompt") or "").strip().split("\n")[0][:200]
    tools = ", ".join(spec.get("tools", [])) or "no tools"
    return f"- {agent_id} ({spec['name']}): {first_line} [{tools}]"


def build_team(team, agent_specs):
    """team = dict from agents.json, agent_specs = {agent_id: spec} of its members"""
    member_ids = [m for m in team["members"] if m in agent_specs]
    if not member_ids:
        raise ValueError("Team has no agents, add some first")

    options = member_ids + ["FINISH"]
    Route = create_model(
        "Route",
        next=(Literal[tuple(options)], Field(description="who acts next, or FINISH")),
        reason=(str, Field(description="one short sentence why")),
        __base__=BaseModel,
    )

    router = get_llm(team["router_model"], temperature=0).with_structured_output(Route)
    # tag it so the streaming code knows not to show router tokens to the user
    router = router.with_config(tags=["router"])

    members_text = "\n".join(_describe(a, agent_specs[a]) for a in member_ids)
    router_system = SystemMessage(ROUTER_PROMPT.format(members=members_text))

    def supervisor(state: TeamState):
        steps = state.get("steps", 0)
        if steps >= config.MAX_TEAM_STEPS:
            return {"next": "FINISH"}

        msgs = [router_system] + state["messages"]
        msgs.append(HumanMessage("Who should act next? Pick one member or FINISH."))
        decision = router.invoke(msgs)

        # first round we always want somebody to actually answer
        if decision.next == "FINISH" and steps == 0:
            return {"next": member_ids[0], "steps": steps}
        return {"next": decision.next, "steps": steps}

    def make_worker(agent_id):
        agent = build_agent(agent_id, agent_specs[agent_id])
        agent_name = agent_specs[agent_id]["name"]

        def worker(state: TeamState):
            msgs = list(state["messages"])
            # if the last message is from another agent, anthropic models treat it as
            # a prefill and just continue it. So give the agent a clear nudge.
            if isinstance(msgs[-1], AIMessage):
                msgs.append(HumanMessage(
                    f"({agent_name}, it's your turn. Build on what was said above, don't repeat it.)"
                ))
            result = agent.invoke({"messages": msgs})
            answer = result["messages"][-1]
            return {
                "messages": [AIMessage(answer.text, name=agent_id)],
                "steps": state.get("steps", 0) + 1,
            }

        return worker

    graph = StateGraph(TeamState)
    graph.add_node("supervisor", supervisor)
    for agent_id in member_ids:
        graph.add_node(agent_id, make_worker(agent_id))
        graph.add_edge(agent_id, "supervisor")

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {**{a: a for a in member_ids}, "FINISH": END},
    )
    return graph.compile()
