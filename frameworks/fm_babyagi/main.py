import sys
import os
import threading

import babyagi

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager

# ---------------------------------------------------------------------------
# This is the current, actively-maintained babyagi (pip install babyagi,
# https://github.com/yoheinakajima/babyagi) - a self-building "functionz"
# framework with a real dashboard, NOT the classic 2023 task-loop version
# used in an earlier version of this integration.
#
# Its ready-made `react_agent` function (in
# babyagi/functionz/packs/drafts/react_agent.py) is a real, complete, bounded
# (max_iterations=5) ReAct-style agent: chain-of-thought reasoning, real
# tool/function-calling against every function registered in babyagi's own
# database, via real litellm.completion() calls - not something written for
# this harness. It is used here instead of the simpler chat_with_functions()
# helper, since it is a genuine multi-step agent loop.
#
# That file originally hardcoded model="gpt-4-turbo", temperature=0.7, and
# max_tokens=1500 with no parameters exposed to override them. Since this is
# a plain installed Python file (not a minified bundle), it has been patched
# directly - see BABYAGI_RUN_README.md for the exact patch, which:
#   - reads the model from BABYAGI_MODEL (falls back to gpt-5.2)
#   - sets temperature=0, max_tokens=1200
#   - uses max_completion_tokens instead of max_tokens for gpt-5.x/o1/o3/o4
#     models (the same OpenAI API change already handled for every other
#     framework in this project)
#
# The shared benchmark system prompt is prepended to each question's input
# text (react_agent only accepts a single `input_text` parameter), matching
# how the other frameworks apply a consistent system-level instruction.
#
# A real dashboard (the project's own advertised feature) can also be run
# alongside, at http://localhost:8080/dashboard, for visual verification -
# see run_dashboard() below. It is optional and separate from the actual
# benchmark loop, which calls babyagi.react_agent() directly in-process.
# ---------------------------------------------------------------------------

BABYAGI_MODEL = os.getenv("BENCHMARK_MODEL") or os.getenv("BABYAGI_MODEL", "gpt-5.2")

_functions_loaded = False


def _ensure_react_agent_loaded():
    global _functions_loaded
    if not _functions_loaded:
        os.environ["BABYAGI_REACT_AGENT_MODEL"] = BABYAGI_MODEL
        babyagi.load_functions('drafts/react_agent')
        _functions_loaded = True


def run_dashboard(port=8080):
    """Optional: run the real babyagi dashboard in a background thread so it
    can be viewed at http://localhost:8080/dashboard alongside the benchmark
    run, for visual verification of registered functions and call logs."""
    app = babyagi.create_app('/dashboard')
    thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    print(f"🌐 BabyAGI dashboard running at http://localhost:{port}/dashboard")


def _call_babyagi(system_prompt, prompt):
    """Calls the real, registered react_agent function directly - a genuine
    bounded ReAct loop, not a single one-shot completion."""
    full_input = f"{system_prompt}\n\n{prompt}"
    try:
        return babyagi.react_agent(input_text=full_input)
    except Exception as e:
        return f"MODEL_ERROR: {e}"


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using the real, pip-installed babyagi's react_agent."""

    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    print(f"🔧 Loading babyagi's react_agent function pack (model={BABYAGI_MODEL})...")
    _ensure_react_agent_loaded()
    print("✅ react_agent loaded and registered")

    if os.getenv("BABYAGI_DASHBOARD", "").lower() in ("1", "true", "yes"):
        run_dashboard()

    system_prompt = dataset_mgr.get_system_prompt()

    for prompt, metadata in dataset_mgr.get_evaluation_iterator("BabyAGI", BABYAGI_MODEL, continue_run, existing_file):
        raw_agent_output = _call_babyagi(system_prompt, prompt)
        dataset_mgr.process_result(raw_agent_output, metadata)

    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("BabyAGI")


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

    print(f"Running BabyAGI {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)

    run_evaluation(dataset_name, mode, continue_run, existing_file)