import sys
import os
import tempfile
import nest_asyncio
from openai import OpenAI

# Enable nested async loops (required for AgentZero)
nest_asyncio.apply()

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using AgentZero with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Initialize AgentZero agent - ONLY framework-specific part
    print("🔧 Initializing AgentZero agent...")
    system_prompt = dataset_mgr.get_system_prompt()
    agent = _initialize_agentzero_agent(system_prompt)
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("AgentZero", "gpt-4.1-mini", continue_run, existing_file):
        # ONLY framework-specific part: agent inference
        try:
            raw_agent_output = agent.monologue(prompt)
        except Exception as e:
            raw_agent_output = f"AGENT_ERROR: {e}"
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def _initialize_agentzero_agent(system_prompt):
    """Initialize simplified AgentZero-style reasoning agent."""
    class AgentZeroSimplified:
        def __init__(self, system_prompt):
            self.client = OpenAI()
            self.temp_dir = tempfile.mkdtemp(prefix="agentzero_")
            self.system_prompt = system_prompt
        
        def monologue(self, message):
            """AgentZero-style monologue interface."""
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": message}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"REASONING_ERROR: {e}"
    
    return AgentZeroSimplified(system_prompt)


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("AgentZero")


if __name__ == "__main__":
    # Parse arguments
    dataset_name = "bbh"
    mode = "sample"
    continue_run = False
    
    # Parse command line arguments
    if "--full" in sys.argv:
        mode = "full"
    if "--continue" in sys.argv:
        continue_run = True
    
    # Check for dataset argument
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