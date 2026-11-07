"""Lab: one brief (the same facts and chart), two scripts: the current rules (v1) and version 2 (RULES_V2.md), written
locally by the production writer (src/make_spec.py `pair`) with the facts from the live game.

  python3 lab/write.py <slot> <category> <name>    -> lab/work/<name>-v1/ and lab/work/<name>-v2/ (spec.json, caption.txt)
Then lab/ab.py times, draws and scores them.
"""
import os, sys

LAB = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(LAB), "src"))
os.environ.setdefault("MS_BASE_LOCAL", "https://memestreet.net")   # (the facts from the live game; the writer on the server asks its own copy)
PACK = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(LAB))), "content", "pack_fiction.json")
if os.path.exists(PACK): os.environ.setdefault("CONTENT_PACK", PACK)   # (the game's companies, from this repo)
import make_spec as M


def claude_cli(messages, system):
    """make_spec.claude_cli, run from the lab folder (it uses /tmp, which this Windows machine does not have)."""
    import subprocess
    convo = "\n\n".join(("REQUEST:\n" if m["role"] == "user" else "YOUR EARLIER REPLY:\n") + m["content"] for m in messages)
    r = subprocess.run(["claude", "-p", "--output-format", "text", "--model", os.environ.get("REEL_CLI_MODEL", "sonnet"),
                        "--append-system-prompt", system,
                        "--disallowedTools", "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,Task,NotebookEdit"],
                       input=convo, capture_output=True, text=True, encoding="utf-8", timeout=600, cwd=LAB,
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})
    if r.returncode: raise SystemExit("claude -p failed: " + (r.stderr or r.stdout)[-400:])
    return r.stdout


M.claude_cli = claude_cli

if __name__ == "__main__":
    slot, category, name = sys.argv[1:4]
    M.pair(slot, *(os.path.join(LAB, "work", f"{name}-{v}") for v in ("v1", "v2")), category)
