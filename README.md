# tiny-harness

A coding agent in 100 lines of Python, with the same parts as Claude Code. It runs free and offline on a local model.

```
$ python agent.py "fix the failing tests"
  → bash {"command": "python -m pytest -q"}
  allow bash {"command": "python -m pytest -q"}? [y/N] y
  → edit_file {"path": "login.py", "old": "hashlib.sha256(password).hexdigest()", ...}
  allow edit_file ...? [y/N] y
```
Tested 2 Nov 2026 on an Apple Silicon Mac with qwen3:14b. It fixed the demo bug, and all 3 tests pass.

## Built with

| Tool | What it does here | Licence |
|---|---|---|
| [Ollama](https://ollama.com) | Runs the model locally and serves an OpenAI-compatible API at `http://localhost:11434/v1` | MIT |
| [Qwen3 14B](https://ollama.com/library/qwen3) | The model. It supports tool calling and thinking | Apache-2.0 |
| [OpenAI Python SDK](https://github.com/openai/openai-python) (`openai` 3.42.0) | Talks to the model: chat completions with `tools` | Apache-2.0 |
| [pytest](https://pytest.org) | The tests the agent runs to check its fix | MIT |
| Python 3 standard library | `subprocess` for bash, `pathlib` for files, `json` for tool arguments | PSF |

## The parts, and where they are in agent.py

| Claude Code has | Real name | In agent.py |
|---|---|---|
| A model (Opus, Sonnet) | LLM | `MODEL`, any OpenAI-compatible endpoint |
| The program around it | harness | the whole file |
| Instructions before your first message | system prompt | `SYSTEM` |
| CLAUDE.md | memory file | loads `AGENTS.md` / `CLAUDE.md` into the system prompt |
| Read, Edit, Bash | tools: name + description + JSON schema | `tool()`, `TOOLS` |
| The model asking to use one | tool call (`finish_reason: "tool_calls"`) | `msg.tool_calls` |
| Output fed back | tool result (`role: "tool"`) | `messages.append({"role": "tool", ...})` |
| Keeps going until done | agent loop | `for _ in range(max_turns)` in `agent()` |
| `/compact` | compaction | `compact()` |
| Task / subagents | subagent with a fresh context window | the `task` tool, which calls `agent(..., depth=1)` |
| "Allow this command?" | permission prompt, human in the loop | `allowed()` |

## Run it

1. **Ollama** (local models): install it from https://ollama.com/download, then pull a model that supports tools:
   ```
   ollama pull qwen3:14b          # about 9 GB. Smaller machines: qwen3:8b
   ```
2. **Context window.** By default, Ollama gives a model a small window (4096 tokens here) and silently drops whatever
   doesn't fit. Restart the server with a bigger one:
   ```
   OLLAMA_CONTEXT_LENGTH=16384 ollama serve
   ```
3. **The harness:**
   ```
   python3 -m venv .venv && .venv/bin/pip install openai pytest
   cd demo && PATH="$PWD/../.venv/bin:$PATH" python ../agent.py "fix the failing tests"
   ```
   Run `demo/reset.sh` to put the bug back.

**Other models.** Point the same code at any OpenAI-compatible API:

```
HARNESS_BASE_URL=https://api.openai.com/v1 HARNESS_API_KEY=sk-... HARNESS_MODEL=<model> python agent.py "..."
```

`--yes` skips the permission prompts. Don't use it outside a throwaway folder: the bash tool runs whatever the model asks for.

## Not safe for real work

This is a teaching harness. Its `bash` tool runs any command it is allowed to, with your user's permissions, and
nothing is sandboxed. Before you point it at a real repository, read each command at its permission prompt, and keep the
project in git.

## Ready-made open-source harnesses

Each of these does the same job with far more polish. Every one is open source and works with Ollama.

| Harness | Install | Run with a local model |
|---|---|---|
| [OpenCode](https://opencode.ai) | `brew install opencode` | add an `ollama` provider in `opencode.json` (`@ai-sdk/openai-compatible`, baseURL `http://localhost:11434/v1`). Tested here with qwen3:14b. |
| [Aider](https://aider.chat) | `python -m pip install aider-install && aider-install` | `aider --model ollama_chat/qwen3:14b` |
| [Goose](https://github.com/aaif-goose/goose) (Agentic AI Foundation, Apache-2.0) | `curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh \| bash` | `goose configure`, then choose Ollama |
| [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | `pip install mini-swe-agent` | `mini` (models through litellm). About 100 lines; the README claims >74% on SWE-bench Verified |

Their docs say the same thing about local models: if tool calls fail, raise the context window (16k–32k tokens).

## Sources
- Ollama OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility
- Tool calling, OpenAI format: https://platform.openai.com/docs/guides/function-calling
- Anthropic, Building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, Effective context engineering for AI agents: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- ReAct (Yao et al., 2022): https://arxiv.org/abs/2210.03629
- Aider + Ollama: https://aider.chat/docs/llms/ollama.html
- OpenCode providers: https://opencode.ai/docs/providers/
