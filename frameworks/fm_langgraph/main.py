import sys
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using LangGraph with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Get system prompt from dataset manager
    system_prompt = dataset_mgr.get_system_prompt()

    # Initialize LangGraph model - ONLY framework-specific part
    print("🔧 Initializing LangGraph model...")
    model = init_chat_model("gpt-4.1-mini", model_provider="openai", temperature=0.0)
    
    # Create ReAct agent with LangGraph
    agent = create_react_agent(
        model,
        tools=[],  # No external tools needed for reasoning tasks
        system_prompt=system_prompt
    )
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("LangGraph", "gpt-4.1-mini", continue_run, existing_file):
        # ONLY framework-specific part: model inference
        try:
            response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
            
            # Extract agent's text response from LangGraph response
            raw_agent_output = ""
            if "messages" in response and response["messages"]:
                # Get the last assistant message
                for msg in reversed(response["messages"]):
                    if hasattr(msg, 'content') and hasattr(msg, 'type'):
                        if msg.type == "ai":
                            raw_agent_output = msg.content
                            break
                    elif isinstance(msg, dict) and msg.get("role") == "assistant":
                        raw_agent_output = msg.get("content", "")
                        break
        except Exception as e:
            raw_agent_output = f"MODEL_ERROR: {e}"
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("LangGraph")


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
    
    print(f"Running LangGraph {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)