import asyncio
import sys
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using Semantic Kernel with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")
    
    # Initialize Semantic Kernel model - ONLY framework-specific part
    print("🔧 Initializing Semantic Kernel model...")
    system_prompt = dataset_mgr.get_system_prompt()
    kernel = Kernel()
    chat_completion = OpenAIChatCompletion(
        service_id="chat-gpt",
        ai_model_id="gpt-4.1-mini"
    )
    kernel.add_service(chat_completion)
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("Semantic Kernel", "gpt-4.1-mini", continue_run, existing_file):
        # ONLY framework-specific part: model inference
        try:
            history = ChatHistory()
            history.add_system_message(system_prompt)
            history.add_user_message(prompt)

            # Run async call synchronously
            result = asyncio.run(chat_completion.get_chat_message_content(
                chat_history=history,
                kernel=kernel,
                settings=OpenAIChatPromptExecutionSettings(
                    max_tokens=1000,
                    temperature=0.0
                )
            ))
            
            raw_agent_output = str(result) if result else ""
        except Exception as e:
            raw_agent_output = f"MODEL_ERROR: {e}"
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("Semantic Kernel")


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
    
    print(f"Running Semantic Kernel {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)