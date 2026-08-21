import sys
import os
import subprocess
import shutil
import time

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager

# ---------------------------------------------------------------------------
# ANUS (https://github.com/anus-dev/ANUS, npm package @anus-dev/anus) is a
# real, complete Node.js CLI coding agent - a fork of Google's gemini-cli,
# repurposed to call xAI's Grok models by default. This script calls the
# real ANUS CLI as a subprocess, non-interactively, redirected to real
# OpenAI (GROK_BASE_URL/GROK_API_KEY/GROK_MODEL all genuinely configurable -
# not a hack, ANUS is built on the standard OpenAI SDK client throughout).
#
# See _call_anus() below for a retry wrapper around a transient,
# internal ANUS/Node.js error observed after many repeated invocations from
# a parent script (confirmed NOT a system file-descriptor limit issue).
# ---------------------------------------------------------------------------

ANUS_MODEL = os.getenv("BENCHMARK_MODEL") or os.getenv("ANUS_MODEL", "gpt-5.2")
ANUS_BASE_URL = os.getenv("ANUS_BASE_URL", "https://api.openai.com/v1")
ANUS_TIMEOUT_SEC = float(os.getenv("ANUS_TIMEOUT_SEC", "500"))
ANUS_CLI_PATH = os.getenv("ANUS_CLI_PATH", "anus")

# How many times to retry a single question if ANUS's own CLI process exits
# with a transient, internal error (observed: "EBADF: bad file descriptor,
# read" - confirmed NOT caused by system file-descriptor limits: manual
# single invocations always succeed even immediately after a failure, and
# both `ulimit -n` and macOS's kernel-wide kern.maxfiles/kern.maxfilesperproc
# were confirmed generous and non-exhausted. This appears to be a real,
# internal bug in the ANUS/Node.js process when spawned repeatedly by a
# parent script - a short retry recovers cleanly every time observed so far.
ANUS_MAX_RETRIES = int(os.getenv("ANUS_MAX_RETRIES", "3"))
ANUS_RETRY_DELAY_SEC = float(os.getenv("ANUS_RETRY_DELAY_SEC", "2"))


def _check_cli_available():
    if shutil.which(ANUS_CLI_PATH) is None:
        raise RuntimeError(
            f"'{ANUS_CLI_PATH}' was not found on PATH. Install it with: "
            "npm install -g @anus-dev/anus"
        )


# ANUS always prints this banner line on stdout before anything else,
# regardless of whether it goes on to produce a real answer.
_ANUS_BANNER_LINES = {"Data collection is disabled."}


def _call_anus_once(system_prompt, prompt):
    """Runs the real ANUS CLI once, non-interactively, redirected to OpenAI.

    --approval-mode yolo auto-approves any tool use so an automated
    benchmark run never hangs waiting for interactive confirmation."""
    full_message = f"{system_prompt}\n\n{prompt}"

    env = os.environ.copy()
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return "MODEL_ERROR: OPENAI_API_KEY is not set"
    env["GROK_API_KEY"] = openai_key
    env["GROK_BASE_URL"] = ANUS_BASE_URL
    env["GROK_MODEL"] = ANUS_MODEL

    try:
        result = subprocess.run(
            [ANUS_CLI_PATH, "--model", ANUS_MODEL, "--approval-mode", "yolo", "--prompt", full_message],
            env=env,
            capture_output=True,
            text=True,
            timeout=ANUS_TIMEOUT_SEC,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return f"MODEL_ERROR: ANUS exited with code {result.returncode}: {result.stderr.strip()[:500]}"

        output_lines = [
            line for line in result.stdout.strip().splitlines()
            if line.strip() not in _ANUS_BANNER_LINES
        ]
        output = "\n".join(output_lines).strip()
        if output:
            return output

        # ANUS exited 0 but produced nothing beyond its startup banner. Seen when
        # an internal ANUS API call (its "checkNextSpeaker" continuation check)
        # fails before ANUS ever generates an answer - e.g. GPT-5-family models
        # reject the max_tokens param ANUS hardcodes there ("Unsupported
        # parameter: 'max_tokens' ... Use 'max_completion_tokens' instead").
        # Surface this as a MODEL_ERROR instead of silently recording the banner
        # text as the agent's answer, which just shows up downstream as a
        # confusing "Failed extraction" with no explanation.
        stderr_excerpt = result.stderr.strip()[:500]
        return f"MODEL_ERROR: ANUS produced no answer (exit 0, only banner output). stderr: {stderr_excerpt}"
    except subprocess.TimeoutExpired:
        return f"MODEL_ERROR: ANUS timed out after {ANUS_TIMEOUT_SEC}s"
    except Exception as e:
        return f"MODEL_ERROR: {e}"


def _call_anus(system_prompt, prompt):
    """Wraps _call_anus_once with a short retry loop specifically for the
    transient EBADF failure pattern described above. Any other kind of
    MODEL_ERROR (timeout, real API error, etc.) is returned immediately
    without retrying, since retrying those would not help and would just
    waste time."""
    last_result = None
    for attempt in range(1, ANUS_MAX_RETRIES + 1):
        result = _call_anus_once(system_prompt, prompt)
        last_result = result
        if not result.startswith("MODEL_ERROR"):
            return result
        if "EBADF" not in result and "bad file descriptor" not in result:
            return result
        if attempt < ANUS_MAX_RETRIES:
            print(f"    ANUS hit a transient EBADF error, retrying ({attempt}/{ANUS_MAX_RETRIES})...")
            time.sleep(ANUS_RETRY_DELAY_SEC)
    return last_result


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using the real ANUS CLI."""

    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    print(f"🔧 Checking ANUS CLI availability (model={ANUS_MODEL}, redirected to {ANUS_BASE_URL})...")
    try:
        _check_cli_available()
        print("✅ ANUS CLI found on PATH")
    except Exception as e:
        print(f"❌ {e}")
        raise

    system_prompt = dataset_mgr.get_system_prompt()

    for prompt, metadata in dataset_mgr.get_evaluation_iterator("ANUS", ANUS_MODEL, continue_run, existing_file):
        raw_agent_output = _call_anus(system_prompt, prompt)
        dataset_mgr.process_result(raw_agent_output, metadata)

    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("ANUS")


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

    print(f"Running ANUS {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)

    run_evaluation(dataset_name, mode, continue_run, existing_file)