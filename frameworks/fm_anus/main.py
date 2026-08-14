import sys
import os
import subprocess
import shutil

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


ANUS_MODEL = os.getenv("BENCHMARK_MODEL") or os.getenv("ANUS_MODEL", "gpt-5.2")
ANUS_BASE_URL = os.getenv("ANUS_BASE_URL", "https://api.openai.com/v1")
ANUS_TIMEOUT_SEC = float(os.getenv("ANUS_TIMEOUT_SEC", "500"))
ANUS_CLI_PATH = os.getenv("ANUS_CLI_PATH", "anus")


def _check_cli_available():
    if shutil.which(ANUS_CLI_PATH) is None:
        raise RuntimeError(
            f"'{ANUS_CLI_PATH}' was not found on PATH. Install it with: "
            "npm install -g @anus-dev/anus"
        )


def _write_anus_md(system_prompt):
    """ANUS's own documented feature ('Project-Aware Context: Uses a local
    ANUS.md file to retain project-specific goals and instructions') is the
    real mechanism for giving it a persistent system-level instruction -
    used here instead of folding the shared benchmark system prompt into
    every per-question message, for consistency with how other frameworks
    apply a fixed system-level instruction throughout a run."""
    with open("ANUS.md", "w") as f:
        f.write(system_prompt)


def _call_anus(prompt):
    """Runs the ANUS CLI once, non-interactively, redirected to OpenAI.

    --approval-mode yolo auto-approves any tool use so an automated
    benchmark run never hangs waiting for interactive confirmation. The
    shared system prompt is not folded into this message - see
    _write_anus_md() above."""
    env = os.environ.copy()
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return "MODEL_ERROR: OPENAI_API_KEY is not set"
    env["GROK_API_KEY"] = openai_key
    env["GROK_BASE_URL"] = ANUS_BASE_URL
    env["GROK_MODEL"] = ANUS_MODEL

    try:
        result = subprocess.run(
            [ANUS_CLI_PATH, "--model", ANUS_MODEL, "--approval-mode", "yolo", "--prompt", prompt],
            env=env,
            capture_output=True,
            text=True,
            timeout=ANUS_TIMEOUT_SEC,
        )
        if result.returncode != 0:
            return f"MODEL_ERROR: ANUS exited with code {result.returncode}: {result.stderr.strip()[:500]}"
        output = result.stdout.strip()
        return output if output else "MODEL_ERROR: empty output from ANUS"
    except subprocess.TimeoutExpired:
        return f"MODEL_ERROR: ANUS timed out after {ANUS_TIMEOUT_SEC}s"
    except Exception as e:
        return f"MODEL_ERROR: {e}"


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
    _write_anus_md(system_prompt)
    print("✅ Wrote shared system prompt to ANUS.md (ANUS's own project-context mechanism)")

    for prompt, metadata in dataset_mgr.get_evaluation_iterator("ANUS", ANUS_MODEL, continue_run, existing_file):
        raw_agent_output = _call_anus(prompt)
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