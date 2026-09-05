# Universe

A small platform for building and running custom AI agents.
Work in progress.
# Universe

A small platform for building and running custom AI agents.
Work in progress.
# Universe

Universe is a small platform for building and orchestrating your own AI agents.
It's a Flask app on top of LangChain + LangGraph, and works with OpenAI and Anthropic models.

- **Dashboard** - all your agents and teams as cards. New agents start from a template (coding assistant, web researcher, data analyst, support, writer) or blank.
- **Builder** - every agent has its own page: config on the left (name, description, model, temperature, instructions, tools), a playground chat on the right. Unsaved changes get saved before each test message, so you just edit and try.
- **Agents** - built with `langchain.agents.create_agent` (a LangGraph ReAct loop under the hood).
- **Teams** - a few agents plus a supervisor model. The supervisor is a LangGraph `StateGraph` that decides which agent talks next and when the answer is done.
- **Streaming** - tokens, tool calls and agent hand-offs are streamed to the browser over SSE.
- **History** - every agent and team has its own thread, saved in `data/chats.json`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # and put your keys in
python app.py
```

Then open http://127.0.0.1:3000 (or run `python starter.py`, it does both).

## How to use

- `/` - dashboard. **New agent** -> pick a template -> you land in the builder.
- `/agents/<id>` and `/teams/<id>` - builder. `Ctrl/Cmd+S` saves, **Reset** clears the playground.
  The playground has its own history, so testing doesn't end up in your real chat.
- `/c/agent:<id>` - full chat. Tabs at the bottom switch agents (`Alt+1..9`), `/copy` or `Ctrl/Cmd+Shift+C` copies the last code block.

On first start you get two agents (Coder, Analyst) and one team (Dev Team = Coder + Analyst).
They live in `data/agents.json`, you can edit that file by hand too.

## Project layout

```
app.py                  Flask routes (pages, agents/teams CRUD, chat stream, history)
universe/
  presets.py            templates for new agents
  config.py             env + paths
  llms.py               model list, ChatOpenAI / ChatAnthropic factory
  tools.py              built-in tools (calculator, current_datetime, fetch_url)
  agents.py             agent spec -> LangGraph agent
  orchestrator.py       team supervisor graph
  runner.py             runs an agent/team, turns the LangGraph stream into UI events
  storage.py            json storage for agents, teams and chats
templates/
  base.html             app shell (sidebar with all agents/teams) + scripts
  dashboard.html        agent / team cards, template picker
  builder.html          config + playground
  chat.html             full screen chat
static/css/universe.css all the styles
static/js/chat.js       streaming chat, shared by builder and chat page
```

## Adding stuff

**A model** - add it to `MODELS` in `universe/llms.py`, or without touching code:

```
UNIVERSE_EXTRA_MODELS=openai:gpt-5.5,anthropic:claude-opus-4-6
```

**A template** - add a dict to `PRESETS` in `universe/presets.py`.

**A tool** - write a function with `@tool` in `universe/tools.py` and add it to `TOOLS`. It shows up in the agent builder right away.
The docstring is what the model sees, so write it properly.

## How a team works

```
START -> supervisor -> agent A -> supervisor -> agent B -> supervisor -> END
```

The supervisor gets the conversation plus a short description of each member (first line of its prompt + tools)
and returns structured output `{next, reason}`. It stops on `FINISH` or after `MAX_TEAM_STEPS` agent turns.
