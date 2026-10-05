---
description: Run an idea through the Believer, Skeptic, Investor and Judge
argument-hint: <idea>
---
Run this idea through the council, strictly in order. Read COUNCIL.md first for earlier verdicts and pass relevant ones along as context.

Idea: $ARGUMENTS

1. Invoke the `believer` subagent with the idea.
2. Invoke the `skeptic` subagent with the idea and the Believer's full output.
3. Invoke the `investor` subagent with the idea and both outputs.
4. Invoke the `judge` subagent with the idea and all three outputs; it appends the verdict to COUNCIL.md.

Run them one at a time (each depends on the previous). Finish by showing the Judge's verdict, biggest risk and 10-minute test, plus a one-line summary of each earlier voice.
