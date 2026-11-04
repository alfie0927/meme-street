# Prewritten reel scripts

`prewritten/<slot>/spec.json` + `caption.txt` (slot = posting time in UTC, `YYYY-MM-DDTHHMM`). When the server's
`auto_reel.sh` makes the reel for a slot, it uses the script here if there is one and only voices and renders it;
otherwise it writes one with Claude itself (`src/make_spec.py`). A cloud session can write them ahead of time.

## How to write one (from `tools/memestreet_daily_reel`)

1. Get the brief (real charts and facts from the live game; it needs internet):

       MS_BASE_LOCAL=https://memestreet.net CONTENT_PACK=../../content/pack_fiction.json \
         python3 src/make_spec.py brief <slot> prewritten/<slot> [--remake remakes/<slot>.json]

   Use `--remake` when `remakes/<slot>.json` exists (a November reel to remake on the same topic). Without it, the
   slot's hour picks the category (03:00 and 21:00 are the viral formats).

2. Read only the instructions and the request, not the whole file (the charts are large):

       python3 -c "import json;B=json.load(open('prewritten/<slot>/brief.json'));print(B['system']);print(json.dumps(B['ask'],indent=1))"

3. Write the reel as the system text asks, as JSON, to `prewritten/<slot>/script.json`.

4. Check and assemble it:

       python3 src/make_spec.py assemble prewritten/<slot>

   If it prints `fix: ...`, fix those things in script.json and run it again. When it passes it writes `spec.json`
   and `caption.txt`. Then delete `brief.json` and `script.json` (the spec has everything).
