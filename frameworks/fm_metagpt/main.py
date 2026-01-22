import os
import sys
from pathlib import Path

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


from metagpt.llm import LLM


async def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using MetaGPT with ultra-clean modular system."""
    
    # Initialize dataset manager with new config - this loads OPENAI_API_KEY
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Get system prompt from dataset manager
    system_prompt = dataset_mgr.get_system_prompt()

    # Create MetaGPT config file now that API key is loaded
    local_config_dir = Path(__file__).parent / "config"
    local_config_dir.mkdir(exist_ok=True)
    local_config_file = local_config_dir / "config2.yaml"
    
    api_key = os.environ.get('OPENAI_API_KEY', '')
    model = os.environ.get('BENCHMARK_MODEL', "gpt-4o-mini")
    
    config_content = f"""llm:
  api_type: "openai"
  model: "{model}"
  base_url: "https://api.openai.com/v1"
  api_key: "{api_key}"
"""
    
    with open(local_config_file, 'w') as f:
        f.write(config_content)
    
    # Initialize MetaGPT model - ONLY framework-specific part
    print("🔧 Initializing MetaGPT model...")
    
    # Update config with current model and API key from environment
    from metagpt.config2 import Config
    config = Config.default()
    config.llm.model = model
    config.llm.api_key = api_key
    
    # Create LLM instance (it uses the global config automatically)
    llm = LLM()
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("MetaGPT", model, continue_run, existing_file):
        # ONLY framework-specific part: model inference
        try:
            # Combine system prompt with user prompt for MetaGPT
            full_prompt = f"{system_prompt}\n\n{prompt}"
            response = await llm.aask(full_prompt)
            raw_agent_output = str(response) if response else ""
        except Exception as e:
            raw_agent_output = f"MODEL_ERROR: {e}"
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("MetaGPT")


if __name__ == "__main__":
    import asyncio
    
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
    
    print(f"Running MetaGPT {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    asyncio.run(run_evaluation(dataset_name, mode, continue_run, existing_file))