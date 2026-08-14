import sys
import os

import requests

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager

# ---------------------------------------------------------------------------
# Agent Zero is a real, self-hosted Docker application - not a script, not a
# pip package. Its own docs state: "The entire framework runs within a
# Docker container." This script talks to a running Agent Zero instance
# over its real REST API (traced directly from its source,
# api/api_message.py) - it does NOT call OpenAI directly. The model itself
# is configured inside Agent Zero's own Settings (Models -> Edit Presets),
# exactly like any agent you'd run through its Web UI.
#
# Before running this:
#   1. docker pull agent0ai/agent-zero
#   2. docker run -d --name agent-zero -p 50080:80 \
#        -v ~/agent-zero-data:/a0/usr \
#        -e OPENAI_API_KEY="sk-..." \
#        agent0ai/agent-zero
#   3. Open http://localhost:50080, go to Settings -> Models -> Edit
#      Presets, and set Main/Utility to OpenAI / gpt-5.2 (or your model),
#      and Embedding to a real embedding model (e.g. OpenAI /
#      text-embedding-3-small - NOT a chat model, it will 403 otherwise).
#      Add your OpenAI key under Settings -> Models -> API Keys.
#   4. Get the server token: open http://localhost:50080/api/settings_get
#      in the same logged-in browser tab and find "mcp_server_token" in the
#      JSON (this field is intentionally blanked in the settings.json file
#      on disk for security - it only appears via this live endpoint).
#      Export it as AGENTZERO_API_KEY.
# ---------------------------------------------------------------------------

AGENTZERO_BASE_URL = os.getenv("AGENTZERO_BASE_URL", "http://localhost:50080/api")
AGENTZERO_API_KEY = os.getenv("AGENTZERO_API_KEY")
AGENTZERO_MODEL = os.getenv("BENCHMARK_MODEL") or os.getenv("AGENTZERO_MODEL", "gpt-5.2")
AGENTZERO_TIMEOUT_SEC = float(os.getenv("AGENTZERO_TIMEOUT_SEC", "500"))


def _headers():
    if not AGENTZERO_API_KEY:
        raise RuntimeError(
            "AGENTZERO_API_KEY is not set. Find the real token at "
            "http://localhost:50080/api/settings_get (look for "
            "'mcp_server_token' in the JSON) and export it."
        )
    return {"X-API-KEY": AGENTZERO_API_KEY, "Content-Type": "application/json"}


def _ask_agent_zero(system_prompt, prompt):
    """Sends one question to the real, running Agent Zero instance via its
    actual /api/api_message endpoint and returns its final answer.

    No context_id is sent, so every question starts a brand new context -
    the same kind of per-question isolation used for the other frameworks
    in this project, so nothing leaks between unrelated benchmark
    questions. The API only accepts a single 'message' field (no separate
    system role), so the shared benchmark system prompt is folded directly
    into the message text."""
    full_message = f"{system_prompt}\n\n{prompt}"
    try:
        resp = requests.post(
            f"{AGENTZERO_BASE_URL}/api_message",
            headers=_headers(),
            json={"message": full_message},
            timeout=AGENTZERO_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            return f"MODEL_ERROR: {data['error']}"
        return data.get("response", "MODEL_ERROR: empty response field")
    except Exception as e:
        return f"MODEL_ERROR: {e}"


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using the real Agent Zero backend."""

    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    print(f"🔧 Connecting to Agent Zero backend at {AGENTZERO_BASE_URL} ...")
    system_prompt = dataset_mgr.get_system_prompt()

    # Quick reachability check before burning through the dataset.
    try:
        requests.post(
            f"{AGENTZERO_BASE_URL}/api_message",
            headers=_headers(),
            json={"message": "Reply with just: ready"},
            timeout=120,
        ).raise_for_status()
        print("✅ Agent Zero is reachable and responding")
    except Exception as e:
        print(f"⚠️  Warning: initial connectivity check failed ({e}). Continuing anyway...")

    for prompt, metadata in dataset_mgr.get_evaluation_iterator("AgentZero", AGENTZERO_MODEL, continue_run, existing_file):
        raw_agent_output = _ask_agent_zero(system_prompt, prompt)
        dataset_mgr.process_result(raw_agent_output, metadata)

    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("AgentZero")


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

    print(f"Running AgentZero {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)

    run_evaluation(dataset_name, mode, continue_run, existing_file)
