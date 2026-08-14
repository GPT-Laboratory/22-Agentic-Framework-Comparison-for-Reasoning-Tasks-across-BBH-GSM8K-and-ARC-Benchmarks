import os
import sys
import time
import json
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager

# psycopg2 is only needed to read the final answer text back out of SuperAGI's
# own Postgres database (see _fetch_final_answer below for why).
try:
    import psycopg2
except ImportError:
    psycopg2 = None


# ---------------------------------------------------------------------------
# SuperAGI connection settings.
#
# IMPORTANT: SuperAGI is not a pip-installable library. It is a self-hosted
# stack (FastAPI backend + Celery + Postgres + Redis + GUI) that you run with
# `docker compose up --build` from a clone of TransformerOptimus/SuperAGI.
# This script talks to that running stack over HTTP (its real REST API) and
# reads back results from its Postgres database. It does NOT call OpenAI
# directly - the OpenAI key lives in SuperAGI's own config.yaml / Model
# Providers settings, exactly like every other agent you create through its
# GUI.
#
# Before running this:
#   1. `git clone https://github.com/TransformerOptimus/SuperAGI.git`,
#      copy config_template.yaml -> config.yaml, fill in OPENAI_API_KEY,
#      then `docker compose up --build` and wait for it to come up on
#      http://localhost:3000
#   2. In the GUI: Settings -> API Keys -> create a key. Export it as
#      SUPERAGI_API_KEY.
#   3. Postgres needs to be reachable from this script. Either uncomment the
#      port mapping for `super__postgres` in docker-compose.yaml
#      (adds "5432:5432") or run this script on the same docker network.
# ---------------------------------------------------------------------------
SUPERAGI_BASE_URL = os.getenv("SUPERAGI_BASE_URL", "http://localhost:3000/api")
SUPERAGI_API_KEY = os.getenv("SUPERAGI_API_KEY")

SUPERAGI_DB_HOST = os.getenv("SUPERAGI_DB_HOST", "localhost")
SUPERAGI_DB_PORT = os.getenv("SUPERAGI_DB_PORT", "5432")
SUPERAGI_DB_NAME = os.getenv("SUPERAGI_DB_NAME", "super_agi_main")
SUPERAGI_DB_USER = os.getenv("SUPERAGI_DB_USER", "superagi")
SUPERAGI_DB_PASSWORD = os.getenv("SUPERAGI_DB_PASSWORD", "password")

SUPERAGI_MODEL = os.getenv("BENCHMARK_MODEL") or os.getenv("SUPERAGI_MODEL", "gpt-5.2")
SUPERAGI_MAX_ITERATIONS = int(os.getenv("SUPERAGI_MAX_ITERATIONS", "5"))
SUPERAGI_POLL_INTERVAL_SEC = float(os.getenv("SUPERAGI_POLL_INTERVAL_SEC", "3"))
SUPERAGI_POLL_TIMEOUT_SEC = float(os.getenv("SUPERAGI_POLL_TIMEOUT_SEC", "900"))

# How many full SuperAGI question-loops to run at the same time. SuperAGI's own
# Celery worker is configured for concurrency=10 (visible in `docker compose
# logs celery`), so it can already handle up to 10 full agent executions in
# parallel - we were only ever using 1 of those 10 slots by running strictly
# one question at a time. This does NOT skip or shorten any SuperAGI step for
# any individual question; it just runs several complete, independent
# question-loops side by side instead of queued single-file. Default of 5
# leaves headroom below SuperAGI's max of 10 and OpenAI rate limits.
SUPERAGI_MAX_CONCURRENT = int(os.getenv("SUPERAGI_MAX_CONCURRENT", "5"))

_AGENT_NAME = "BBH-Eval-Agent-v2"


def _headers():
    if not SUPERAGI_API_KEY:
        raise RuntimeError(
            "SUPERAGI_API_KEY is not set. Create one in the SuperAGI GUI "
            "under Settings -> API Keys and export it as SUPERAGI_API_KEY."
        )
    return {"X-API-Key": SUPERAGI_API_KEY, "Content-Type": "application/json"}


def _find_existing_agent():
    """Check SuperAGI's own database for an agent we already created in a
    previous run, so repeated runs reuse the same agent instead of leaving
    behind a new one every single time."""
    if psycopg2 is None:
        return None
    conn = psycopg2.connect(
        host=SUPERAGI_DB_HOST, port=SUPERAGI_DB_PORT, dbname=SUPERAGI_DB_NAME,
        user=SUPERAGI_DB_USER, password=SUPERAGI_DB_PASSWORD,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM agents WHERE name = %s AND is_deleted = false ORDER BY id DESC LIMIT 1",
                (_AGENT_NAME,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def _get_or_create_agent(system_prompt):
    """Reuse the persistent agent from a previous run if one already exists
    (checked directly in SuperAGI's own database); otherwise create it once
    via SuperAGI's real /api/v1/agent endpoint."""
    existing_id = _find_existing_agent()
    if existing_id is not None:
        return existing_id

    payload = {
        "name": _AGENT_NAME,
        "description": "Reasoning-benchmark agent (ARC/GSM8K/BBH eval harness)",
        "goal": ["Answer the question accurately with clear reasoning."],
        "instruction": [system_prompt],
        "agent_workflow": "Goal Based Workflow",
        "constraints": [],
        "tools": [],
        "exit": "No exit criterion",
        "permission_type": "God Mode",
        "LTM_DB": None,
        "iteration_interval": 1,
        "model": SUPERAGI_MODEL,
        "max_iterations": SUPERAGI_MAX_ITERATIONS,
        "user_timezone": "UTC",
        "knowledge": None,
    }
    resp = requests.post(f"{SUPERAGI_BASE_URL}/v1/agent", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["agent_id"]


def _fix_iteration_workflow_step_id(run_id):
    """SuperAGI's own /run endpoint has a real bug: it sets current_agent_step_id
    on new executions but never sets iteration_workflow_step_id, which is the
    field agent_iteration_step_handler.py actually reads. Without it, every
    single reasoning step crashes instantly with
    'NoneType' object has no attribute 'prompt', and the execution silently
    loops forever without ever making progress. We work around this by setting
    it ourselves, directly in SuperAGI's own database, right after starting
    the run - using the same starting step ID (1) that a correctly-initialized
    execution (created the very first time, through a different code path)
    already uses."""
    if psycopg2 is None:
        return
    conn = psycopg2.connect(
        host=SUPERAGI_DB_HOST, port=SUPERAGI_DB_PORT, dbname=SUPERAGI_DB_NAME,
        user=SUPERAGI_DB_USER, password=SUPERAGI_DB_PASSWORD,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE agent_executions SET iteration_workflow_step_id = 1 WHERE id = %s AND iteration_workflow_step_id IS NULL",
                (run_id,),
            )
        conn.commit()
    finally:
        conn.close()


def _start_run(agent_id, prompt):
    """Kick off a fresh run on the existing agent with this question as the
    goal, via the real /api/v1/agent/{id}/run endpoint."""
    payload = {"name": "eval-run", "goal": [prompt], "instruction": None}
    resp = requests.post(f"{SUPERAGI_BASE_URL}/v1/agent/{agent_id}/run", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    run_id = resp.json()["run_id"]
    _fix_iteration_workflow_step_id(run_id)
    return run_id


def _poll_run_status(agent_id, run_id):
    """Poll the real /api/v1/agent/{id}/run-status endpoint until the run
    finishes, errors out, or we time out."""
    deadline = time.time() + SUPERAGI_POLL_TIMEOUT_SEC
    while time.time() < deadline:
        resp = requests.post(
            f"{SUPERAGI_BASE_URL}/v1/agent/{agent_id}/run-status",
            headers=_headers(),
            json={"run_ids": [run_id]},
            timeout=30,
        )
        resp.raise_for_status()
        runs = resp.json()
        status = next((r["status"] for r in runs if r["run_id"] == run_id), None)
        if status in ("COMPLETED", "ERROR", "TERMINATED", "ITERATION_LIMIT_EXCEEDED"):
            return status
        time.sleep(SUPERAGI_POLL_INTERVAL_SEC)
    return "TIMEOUT"


def _fetch_final_answer(run_id):
    """SuperAGI's API-key-authenticated routes don't expose the final answer
    text (only the JWT/GUI session routes do). Since this is our own local
    stack, read the answer straight out of its `agent_execution_feeds` table
    instead of scraping the GUI or faking a login."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required to read results back from SuperAGI's Postgres DB.")

    conn = psycopg2.connect(
        host=SUPERAGI_DB_HOST,
        port=SUPERAGI_DB_PORT,
        dbname=SUPERAGI_DB_NAME,
        user=SUPERAGI_DB_USER,
        password=SUPERAGI_DB_PASSWORD,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT feed, role FROM agent_execution_feeds
                WHERE agent_execution_id = %s
                ORDER BY id DESC
                """,
                (run_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    for feed, role in rows:
        if role != "assistant":
            continue
        # Assistant feeds are usually JSON (thoughts/tool/command). Try to
        # pull a human-readable result out of common shapes; otherwise fall
        # back to the raw text.
        try:
            parsed = json.loads(feed)
        except (json.JSONDecodeError, TypeError):
            return feed
        for key in ("speak", "result", "response", "final_answer", "text"):
            if isinstance(parsed, dict) and parsed.get(key):
                return str(parsed[key])
        if isinstance(parsed, dict) and "thoughts" in parsed:
            return json.dumps(parsed["thoughts"])
        return feed

    # No assistant feed found at all - return whatever came back so it's at
    # least visible in the results file instead of silently empty.
    return rows[0][0] if rows else ""


def _run_one_question(agent_pool, prompt):
    """Runs one question through the COMPLETE, real SuperAGI agent loop -
    nothing shortened or skipped. Checks out a dedicated agent from the pool
    (never shared with another concurrently-running question) and returns it
    when done, so no two simultaneous runs ever touch the same agent_id."""
    agent_id = agent_pool.get()
    try:
        run_id = _start_run(agent_id, prompt)
        status = _poll_run_status(agent_id, run_id)
        if status == "COMPLETED":
            return _fetch_final_answer(run_id)
        return f"MODEL_ERROR: SuperAGI run ended with status={status}"
    except Exception as e:
        return f"MODEL_ERROR: {e}"
    finally:
        agent_pool.put(agent_id)


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using the real SuperAGI backend with ultra-clean modular system."""

    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    print("🔧 Connecting to SuperAGI backend...")
    system_prompt = dataset_mgr.get_system_prompt()

    # One dedicated agent per concurrent worker slot - never shared between
    # simultaneously-running questions, to rule out any cross-talk between
    # concurrent runs on SuperAGI's side.
    agent_pool = queue.Queue()
    agent_ids = []
    for _ in range(SUPERAGI_MAX_CONCURRENT):
        aid = _get_or_create_agent(system_prompt)
        agent_ids.append(aid)
        agent_pool.put(aid)
    print(f"✅ Created {len(agent_ids)} dedicated SuperAGI agents for concurrent use: {agent_ids}")
    print(f"⚙️  Running up to {SUPERAGI_MAX_CONCURRENT} questions concurrently "
          f"(each still runs SuperAGI's full, unmodified reasoning loop, on its own agent)")

    pending = {}
    with ThreadPoolExecutor(max_workers=SUPERAGI_MAX_CONCURRENT) as executor:
        iterator = dataset_mgr.get_evaluation_iterator("SuperAGI", SUPERAGI_MODEL, continue_run, existing_file)
        for prompt, metadata in iterator:
            future = executor.submit(_run_one_question, agent_pool, prompt)
            pending[future] = metadata

            while len(pending) >= SUPERAGI_MAX_CONCURRENT:
                done = next(as_completed(list(pending.keys())))
                meta = pending.pop(done)
                dataset_mgr.process_result(done.result(), meta)

        # Drain whatever's still in flight once the dataset is exhausted.
        for done in as_completed(list(pending.keys())):
            meta = pending.pop(done)
            dataset_mgr.process_result(done.result(), meta)

    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("SuperAGI")


if __name__ == "__main__":
    dataset_name = "bbh"
    mode = "sample"
    continue_run = False

    if "--full" in sys.argv:
        mode = "full"
    if "--continue" in sys.argv:
        continue_run = True

    for arg in sys.argv:
        if arg.startswith("--dataset="):
            dataset_name = arg.split("=")[1]

    existing_file = None
    if continue_run:
        existing_file = find_latest_results_file(dataset_name, mode)
        if not existing_file:
            print(f"❌ No existing results file found for {dataset_name} ({mode} mode)")
            sys.exit(1)
        print(f"📂 Found existing file: {existing_file}")

    print(f"Running SuperAGI {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)

    run_evaluation(dataset_name, mode, continue_run, existing_file)