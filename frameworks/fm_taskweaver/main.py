import sys
import os

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using TaskWeaver with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")
    
    # Initialize TaskWeaver model - ONLY framework-specific part
    print("🔧 Initializing TaskWeaver model...")
    system_prompt = dataset_mgr.get_system_prompt()

    # Set up TaskWeaver environment
    try:
        # Add TaskWeaver repo to path
        sys.path.insert(0, 'taskweaver_repo')
        
        from taskweaver.app.app import TaskWeaverApp
        
        # Initialize TaskWeaver app with project directory
        project_dir = "./taskweaver_project"
        if not os.path.exists(project_dir):
            os.makedirs(project_dir, exist_ok=True)
        
        # Copy config to project directory
        config_source = "./taskweaver_config.json"
        config_dest = f"{project_dir}/taskweaver_config.json"
        import shutil
        if os.path.exists(config_source):
            shutil.copy2(config_source, config_dest)
        
        app = TaskWeaverApp(app_dir=project_dir)
        
    except Exception as e:
        raise RuntimeError(f"TaskWeaver initialization failed: {e}")
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("TaskWeaver", "gpt-4.1-mini", continue_run, existing_file):
        # ONLY framework-specific part: model inference
        try:
            # Get a fresh session
            session = app.get_session()
            
            # Send the system prompt first, then the user prompt
            # TaskWeaver doesn't have explicit system prompt support, so we prepend it
            full_prompt = f"{system_prompt}\n\nUser Question: {prompt}"
            response_round = session.send_message(full_prompt)
            
            # Extract response text from TaskWeaver response format
            response_text = ""
            if hasattr(response_round, 'post_list') and response_round.post_list:
                # Get the assistant's response (usually the last post)
                for post in response_round.post_list:
                    if hasattr(post, 'message') and post.message:
                        response_text += post.message + "\n"
            
            if not response_text:
                response_text = str(response_round)
            
            raw_agent_output = response_text.strip()
        except Exception as e:
            raw_agent_output = f"MODEL_ERROR: {e}"
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("TaskWeaver")


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
    
    print(f"Running TaskWeaver {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)