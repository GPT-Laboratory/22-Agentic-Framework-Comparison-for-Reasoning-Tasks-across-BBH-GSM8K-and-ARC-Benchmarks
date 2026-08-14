# SuperAGI Benchmark — Full Setup & Recovery Guide

This covers everything needed to set this up from scratch on a new machine,
and to start (or resume, e.g. after a crash/reboot) the SuperAGI benchmark
run against BBH/GSM8K/ARC.

You will end up with **three terminal tabs**, each with one job. Don't type
benchmark commands into the Docker tab, and don't type Docker commands into
the benchmark tab — keeping them separate avoids a lot of confusion.

---

## Part A — One-Time Initial Setup (only needed once, ever, on a new machine)

Skip straight to **Part B** if this is already set up and you're just
starting/resuming a run.

### A1. Open Docker Desktop
`Cmd + Space` → type `Docker` → `Enter` → wait ~30-60s for the whale icon 🐳
in the menu bar to settle.

### A2. Clone SuperAGI and configure it
```bash
git clone https://github.com/TransformerOptimus/SuperAGI.git
cd SuperAGI
cp config_template.yaml config.yaml
```
Open `config.yaml` and set your OpenAI key:
```yaml
OPENAI_API_KEY: sk-your-real-key-here
```

### A3. Expose Postgres to your host
In `docker-compose.yaml`, find the `super__postgres` service and make sure
its `ports:` block is uncommented:
```yaml
    ports:
      - "5432:5432"
```

### A4. Build and start the stack (first time only — this takes 5-10 minutes)
```bash
docker compose -f docker-compose.yaml up --build
```
Wait for it to settle, then leave it running (or switch to detached mode —
see Part B, Step 1).

### A5. Open the SuperAGI GUI and sign up
Browser → `localhost:3000` → sign up with any email/password (this is a
local-only account).

### A6. Add your OpenAI key inside the GUI itself
Gear/settings icon (top-right) → **Model Providers** tab → paste your OpenAI
key under "Open AI API key" → save.
(This is separate from the key in `config.yaml` — SuperAGI needs it in both places.)

### A7. Register your model (e.g. `gpt-5.2`) as a custom model
SuperAGI only auto-recognizes `gpt-3.5-turbo`, `gpt-4`, and
`gpt-3.5-turbo-16k` out of the box. Any other model (like `gpt-5.2`) needs to
be added manually:
- Click **Models** in the left sidebar → **Add Model**
- **Name**: `gpt-5.2` (must exactly match what you'll use later)
- **Model Provider**: OpenAI
- **Token Limit**: `128000` (or the model's real context length if known)
- Save

### A8. Get your SuperAGI API key
Gear/settings icon → **API Keys** tab → create a key → copy it somewhere safe.
This is what authenticates the benchmark script to your local SuperAGI
server — it's a completely different credential from your OpenAI key.

Setup is now done. Move to Part B for the actual day-to-day run.

---

## Part B — Every Time You Start or Resume

### Step 1 — Terminal 1: Docker

Open Docker Desktop if it isn't already running (`Cmd+Space` → `Docker`).

Open a Terminal window:
```bash
cd /Users/hxzera/Documents/Agentic_Framework_FinalCode/bbh_test-main/SuperAGI
docker compose -f docker-compose.yaml up -d
docker compose ps
```
Confirm all 6 containers (`backend`, `celery`, `gui`, `proxy`,
`super__postgres`, `super__redis`) show `Up`.

Then check there's no leftover backlog from a previous crash:
```bash
docker compose exec celery celery -A superagi.worker inspect active
```
Should print `- empty -`. If not:
```bash
docker compose restart celery
docker compose exec celery celery -A superagi.worker purge -f
docker compose exec celery celery -A superagi.worker inspect active
```
Confirm empty again.

**Leave this terminal tab alone from here on.**

### Step 2 — Terminal 2: Keep the Mac awake

New tab (`Cmd+T`):
```bash
caffeinate -i
```
Leave it running — it prints nothing, that's normal. Also keep the Mac
**plugged in** and the **lid open**; a closed lid can force sleep even with
`caffeinate` running.

### Step 3 — Terminal 3: Run the benchmark

New tab:
```bash
export SUPERAGI_API_KEY="your-superagi-key"
export SUPERAGI_DB_PASSWORD="password"
export SUPERAGI_MAX_CONCURRENT=1
```

(Your `OPENAI_API_KEY` should already be permanent in `~/.zshrc` — check with
`echo $OPENAI_API_KEY`. If wrong/revoked:
`sed -i '' 's|export OPENAI_API_KEY=.*|export OPENAI_API_KEY="sk-your-new-key"|' ~/.zshrc && source ~/.zshrc`)

```bash
cd /Users/hxzera/Documents/Agentic_Framework_FinalCode/bbh_test-main/frameworks/fm_superagi
```

**Check nothing's already running first:**
```bash
ps aux | grep "main.py"
```

**Starting completely fresh** (new dataset, or known-bad prior data):
```bash
nohup uv run main.py --full > full_run_log.txt 2>&1 &
```

**Resuming an interrupted run** (the normal case after a crash/pause):
```bash
nohup uv run main.py --full --continue > full_run_log.txt 2>&1 &
```

For a different dataset: add `--dataset=arc` or `--dataset=gsm8k`.

Confirm it started:
```bash
ps aux | grep "main.py"
```

---

## Checking Progress (safe anytime, run as often as you like)

```bash
cd /Users/hxzera/Documents/Agentic_Framework_FinalCode/bbh_test-main/frameworks/fm_superagi
python3 /tmp/check_progress.py
```

If that script doesn't exist yet:
```bash
cat > /tmp/check_progress.py << 'PYEOF'
import json, glob, os
from collections import Counter

files = sorted(glob.glob('outputs/*full*.json'), key=os.path.getmtime)
latest = files[-1]
with open(latest) as f:
    data = json.load(f)

results = data['detailed_results']
print('File:', latest)
print('Total so far:', len(results))
print('Correct:', sum(1 for r in results if r['is_correct']))

error_types = Counter()
for r in results:
    if not r['is_correct']:
        raw = str(r.get('raw_agent_output', ''))
        if raw.startswith('MODEL_ERROR'):
            error_types[raw[:60]] += 1
        elif not r['extracted_answer']:
            error_types['extraction_failed_had_output'] += 1
        else:
            error_types['wrong_answer_extraction_worked'] += 1

print()
print('Breakdown of non-correct results:')
for k, v in error_types.most_common(20):
    print('  {:4d}  {}'.format(v, k))
PYEOF
python3 /tmp/check_progress.py
```

**Healthy output**: mostly `Correct`, some `wrong_answer_extraction_worked`
and `extraction_failed_had_output` (both normal), and **zero or very few
`MODEL_ERROR: ... TIMEOUT`**. A wall of `TIMEOUT`s means something regressed
— see Troubleshooting below.

---

## Stopping Cleanly (before going out, closing the laptop, etc.)

```bash
ps aux | grep "main.py"
kill -9 <the two PIDs shown, not the grep line>
ps aux | grep "main.py"
```
Confirms only the `grep` line remains. Your progress is already saved on
disk — nothing is lost. At most, the one question that was actively
in-progress gets re-attempted when you resume with `--continue`.

---

## What's Actually Inside `main.py` (for reference / defending the results)

`main.py` does NOT call OpenAI directly — it talks to this real, self-hosted
SuperAGI instance over its actual REST API, and reads answers back out of
SuperAGI's own Postgres database. Three real bugs in SuperAGI's own code were
found and fixed along the way:

1. **`max_tokens` not supported by newer models** — SuperAGI's `openai.py`
   hardcoded the old parameter name; newer models require
   `max_completion_tokens`. Patched with a conditional based on model name.
2. **Invalid FastAPI usage** (`request: Request = Depends()`) in
   `superagi/helper/auth.py` — an upstream bug, fixed by editing that file
   directly (bind-mounted from your local clone).
3. **The big one**: SuperAGI's own `/v1/agent/{id}/run` endpoint never sets
   `iteration_workflow_step_id` on new executions — every reasoning step then
   crashes instantly with `'NoneType' object has no attribute 'prompt'`,
   silently looping forever. `main.py` works around this by setting the
   correct value directly in Postgres right after every `/run` call.

Other design points:
- **Agent reuse**: checks Postgres for an existing agent named
  `BBH-Eval-Agent-v2` before creating a new one.
- **`max_iterations=5`, timeout=900s**: tuned around the discovery that
  SuperAGI's Celery Beat only advances multi-step reasoning every 2 minutes.
- **Answer extraction** (mapping SuperAGI's raw output to a clean target
  class) is separate, shared code (`frameworks/utils.py` /
  `frameworks/datasets.yml`).

---

## Troubleshooting

**Seeing lots of `TIMEOUT` again:**
1. Stop the run, clear the Celery backlog (Step 1's purge commands).
2. Check a recent execution directly:
   ```bash
   docker compose exec super__postgres psql -U superagi -d super_agi_main \
     -c "SELECT id, status, num_of_calls, iteration_workflow_step_id FROM agent_executions ORDER BY id DESC LIMIT 5;" | cat
   ```
   `iteration_workflow_step_id` should show `1`, not blank. If blank, confirm
   you're running the fixed `main.py` (`grep _fix_iteration_workflow_step_id main.py`).
3. Resume with `--continue` once healthy.

**Two copies running at once:** `ps aux | grep "main.py"` → kill the older pair only.

**Docker containers missing after a reboot:** `docker compose -f docker-compose.yaml up -d`

**Stale environment variable:** `export` only lasts for that terminal session — always re-export in a fresh tab.

---

## Quick Reference — All Commands In Order

```bash
# Terminal 1 (Docker)
cd /Users/hxzera/Documents/Agentic_Framework_FinalCode/bbh_test-main/SuperAGI
docker compose -f docker-compose.yaml up -d
docker compose ps
docker compose exec celery celery -A superagi.worker inspect active

# Terminal 2 (keep awake)
caffeinate -i

# Terminal 3 (benchmark)
export SUPERAGI_API_KEY="your-key"
export SUPERAGI_DB_PASSWORD="password"
export SUPERAGI_MAX_CONCURRENT=1
cd /Users/hxzera/Documents/Agentic_Framework_FinalCode/bbh_test-main/frameworks/fm_superagi
nohup uv run main.py --full --continue > full_run_log.txt 2>&1 &
ps aux | grep "main.py"

# Check progress (any time, any terminal)
cd /Users/hxzera/Documents/Agentic_Framework_FinalCode/bbh_test-main/frameworks/fm_superagi
python3 /tmp/check_progress.py
```
