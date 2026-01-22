import sys
from agency_swarm import Agent, Agency

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using Agency Swarm with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Initialize Agency Swarm model - ONLY framework-specific part
    print("🔧 Initializing Agency Swarm model...")
    system_prompt = dataset_mgr.get_system_prompt()
    bbh_solver = Agent(
        name="BBHSolver",
        description="Expert reasoning agent specialized in solving complex logical, mathematical, and analytical problems step-by-step.",
        instructions=system_prompt,
        model="gpt-4.1-mini",
        temperature=0.0,
        max_prompt_tokens=25000,
        tools=[]
    )
    
    agency = Agency([bbh_solver])
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("Agency Swarm", "gpt-4.1-mini", continue_run, existing_file):
        # ONLY framework-specific part: model inference
        try:
            response = agency.get_completion(
                message=prompt,
                yield_messages=False
            )
            
            # Extract text content from response
            if isinstance(response, str):
                raw_agent_output = response
            elif hasattr(response, 'content'):
                raw_agent_output = response.content
            elif hasattr(response, 'message'):
                raw_agent_output = response.message
            else:
                raw_agent_output = str(response)
        except Exception as e:
            raw_agent_output = f"MODEL_ERROR: {e}"
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("Agency Swarm")


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
    
    print(f"Running Agency Swarm {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)