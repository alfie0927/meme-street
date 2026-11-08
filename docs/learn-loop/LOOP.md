# The Learn loop: one iteration

You are improving the Learn section of Meme Street (`/learn`) until it meets `docs/learn-loop/RUBRIC.md`. One
iteration is one finding fixed, tested, documented and committed. Run it with
`/loop Follow docs/learn-loop/LOOP.md for one iteration` (self-paced) or by hand. Project rules apply: read
`docs/ROADMAP.md` before starting, update `docs/HOW_IT_WORKS.md` after a change, files in their folders.

## Steps

1. **Orient.** Read `docs/learn-loop/LEDGER.md` (the last rows: what was done, what is left, what the owner marked
   "do next" or "won't do") and `RUBRIC.md`. Run `git log -3 --oneline` and `git status --short`. If files you did
   not touch changed since the last ledger row, another session is working in the tree: stop and report instead of
   editing.
2. **Measure.** From `D:\stock_market_sim`: `python tools/learn_check.py`; from `tests/`:
   `python -m unittest test_learning test_drills`; `node --check web/learn.js`; parse the inline script of
   `web/index.html` with node. **Any failure is this iteration's finding**: fix it and go to step 5.
3. **Walk through.** Otherwise run one simulated learner as an Explore agent (read-only; GET to the local server
   allowed, never POST), rotating C1, C2, C3 from the rubric, with its 20-point checklist verbatim. It returns the
   score and its findings ranked by size with the fix it would make. Take the top finding that the ledger does not
   mark "won't do" (the owner's "do next" rows come first). A persona scoring 18 or more with nothing of size S or
   larger is marked **clean** in the ledger.
4. **Fix.** The smallest change that closes the finding, written as a re-runnable patch script in the scratchpad
   (exact-string edits, CRLF-tolerant, skipping edits already applied), then run. Content edits by hand only in the
   units the rubric names. Add or adjust a test when logic changed. Update `docs/HOW_IT_WORKS.md` §10.10 and the
   roadmap's LP line. Rerun step 2; if it cannot be made green, revert your own edits (`git checkout -- <files>`) and
   record the attempt as failed with the reason.
5. **Restart the local server:** kill the listener on port 8000 (`netstat -ano | grep :8000`, `taskkill //PID <pid>
   //F //T`), start `.venv/Scripts/python.exe -m uvicorn server:app --app-dir game --host 127.0.0.1 --port 8000`
   with `ADMIN_KEY` from `data/admin_key.txt` and `PAYMENTS=test` as a background task (no `--reload`: it hangs here),
   check `/api/health`.
6. **Commit.** `git add` the files you touched (never `-a`, never `data/`, never another session's files), commit
   with one line naming the finding, e.g. `Learn loop 7: questions interleaved in Market basics`, and the attribution
   line the session requires. Append the ledger row (iteration, date, B result, C score, finding, change, files,
   commit hash, what is left) and commit it too.
7. **Stop or continue.** Stop and write a final report row when: B passes, C1-C3 are each marked clean in their last
   run, and two consecutive iterations found nothing of size S or larger. Stop after iteration 12 regardless, with a
   report. Otherwise schedule the next iteration in a few minutes (nothing external to wait for).
8. **Report** to the owner in one short message: score, finding, change, commit hash.

## Guard rails

- Never deploy, never push, never touch `data/`, never run the whole test suite, never commit with `-a`.
- One finding per iteration. Keep diffs small; the smallest change that works.
- The design rules hold: nothing on the Learn page pays MB; nothing moves a price; players' progress is theirs.
- The owner steers through the ledger: a row marked **do next** goes first; **won't do** is skipped for good.
- If the owner is in the terminal and asks something, answer, then continue the iteration.
