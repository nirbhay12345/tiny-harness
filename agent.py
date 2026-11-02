"""tiny-harness: a coding agent in about 100 lines. Same parts as Claude Code, all open source.

    python agent.py "fix the failing test in login.py"

Model: any OpenAI-compatible endpoint. Default is a local model on Ollama (free, offline).
    HARNESS_BASE_URL=http://localhost:11434/v1  HARNESS_MODEL=qwen3:14b
"""
import json, os, subprocess, sys
from pathlib import Path
from openai import OpenAI

client = OpenAI(base_url=os.getenv("HARNESS_BASE_URL", "http://localhost:11434/v1"),
                api_key=os.getenv("HARNESS_API_KEY", "ollama"))
MODEL = os.getenv("HARNESS_MODEL", "qwen3:14b")
MAX_CHARS = int(os.getenv("HARNESS_MAX_CHARS", "40000"))   # ~10k tokens: start Ollama with OLLAMA_CONTEXT_LENGTH=16384
AUTO_YES = "--yes" in sys.argv

# System prompt, plus project memory files (AGENTS.md is the open convention, CLAUDE.md is Claude Code's).
SYSTEM = "You are a coding agent in " + os.getcwd() + ". Use the tools to read, run and edit code. " \
         "Check your work by running the tests. Reply without a tool call only when the task is done."
for f in ("AGENTS.md", "CLAUDE.md"):
    if Path(f).exists():
        SYSTEM += f"\n\n# {f}\n" + Path(f).read_text()


def tool(name, desc, **params):   # one tool definition = a name, a description and a JSON schema
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": {k: {"type": "string", "description": v} for k, v in params.items()},
        "required": list(params)}}}


TOOLS = [tool("read_file", "Read a text file.", path="file path"),
         tool("edit_file", "Replace one exact snippet in a file (empty old creates the file).",
              path="file path", old="exact text to replace", new="replacement text"),
         tool("bash", "Run a shell command, e.g. pytest. Returns stdout and stderr.", command="the command"),
         tool("task", "Hand a self-contained subtask to a subagent with a fresh context; returns its summary.",
              prompt="the full subtask")]


def allowed(name, args):          # permission prompt: anything that changes the machine asks first
    if AUTO_YES or name in ("read_file", "task"):
        return True
    return input(f"\n  allow {name} {json.dumps(args)[:200]}? [y/N] ").strip().lower() == "y"


def run_tool(name, args):
    if not allowed(name, args):
        return "denied by the user"
    try:
        if name == "read_file":
            return Path(args["path"]).read_text()
        if name == "edit_file":
            p = Path(args["path"])
            text = p.read_text() if p.exists() else ""
            if args["old"] and text.count(args["old"]) != 1:
                return "error: old text must appear exactly once"
            p.write_text(text.replace(args["old"], args["new"], 1) if args["old"] else args["new"])
            return f"edited {p}"
        if name == "bash":
            r = subprocess.run(args["command"], shell=True, capture_output=True, text=True, timeout=120)
            return (r.stdout + r.stderr)[-8000:] or f"(exit {r.returncode})"
        if name == "task":
            return agent(args["prompt"], depth=1)   # subagent: same loop, empty context
    except Exception as e:
        return f"error: {e}"
    return f"error: unknown tool {name}"


def compact(messages):            # compaction: summarise old turns when the context window fills up
    if sum(len(str(m.get("content") or "")) for m in messages) < MAX_CHARS:
        return messages
    old, recent = messages[1:-6], messages[-6:]
    while recent and recent[0].get("role") == "tool":   # never start on an orphaned tool result
        old.append(recent.pop(0))
    summary = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content":
              "Summarise this agent session: goal, files touched, what is done, what is left.\n\n" +
              json.dumps(old, default=str)[-MAX_CHARS:]}]).choices[0].message.content
    print("  [compacted older turns]")
    return [messages[0], {"role": "user", "content": "Summary of earlier work:\n" + summary}] + recent


def agent(task, depth=0, max_turns=30):
    tools = TOOLS if depth == 0 else TOOLS[:3]           # subagents can't spawn subagents
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    for _ in range(max_turns):                           # the agent loop
        messages = compact(messages)
        msg = client.chat.completions.create(model=MODEL, messages=messages, tools=tools).choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:                           # no tool call: the model says it is done
            return msg.content
        for call in msg.tool_calls:                      # finish_reason == "tool_calls": run them
            args = json.loads(call.function.arguments or "{}")
            print(f"{'  ' * (depth + 1)}→ {call.function.name} {json.dumps(args)[:100]}")
            result = run_tool(call.function.name, args)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
    return "stopped: turn limit reached"


if __name__ == "__main__":
    print(agent(" ".join(a for a in sys.argv[1:] if a != "--yes")))
