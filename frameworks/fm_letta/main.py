import sys
from letta_client import Letta, CreateBlock, MessageCreate
from datetime import datetime

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


def extract_agent_response(response):
    """Extract the final text response from Letta's message structure."""
    if not response or not hasattr(response, 'messages') or not response.messages:
        return ""
    
    # Find the last assistant message with content
    for message in reversed(response.messages):
        if hasattr(message, 'role') and message.role == 'assistant':
            if hasattr(message, 'content') and message.content:
                return message.content.strip()
        # Also check for dict format
        elif isinstance(message, dict) and message.get('role') == 'assistant':
            content = message.get('content', '')
            if content:
                return content.strip()
    
    # If no assistant message found, try to get any text content
    for message in response.messages:
        if hasattr(message, 'content') and message.content:
            return message.content.strip()
        elif isinstance(message, dict) and message.get('content'):
            return message['content'].strip()
    
    return ""


def create_letta_client():
    """Create and validate Letta client connection."""
    try:
        client = Letta(base_url="http://localhost:8283")
        return client
    except Exception as e:
        print(f"❌ Error connecting to Letta server: {e}")
        print("   Make sure Letta server is running via: ./setup.sh")
        raise


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using Letta with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Get system prompt from dataset manager
    system_prompt = dataset_mgr.get_system_prompt()

    # Initialize Letta client and create agent - ONLY framework-specific part
    print("🔗 Connecting to Letta server...")
    client = create_letta_client()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = "gpt-4.1-mini"  # Default model for Letta
    
    print("🧠 Creating Letta agent for evaluation...")
    try:
        agent_state = client.agents.create(
            name=f"eval_{dataset_name}_{timestamp}",
            model=f"openai/{model_name}" if not model_name.startswith("openai/") else model_name,
            embedding="openai/text-embedding-3-small",
            memory_blocks=[
                CreateBlock(
                    label="human",
                    value="User requesting reasoning task completion. Provide clear, step-by-step solutions."
                ),
                CreateBlock(
                    label="persona",
                    value=system_prompt
                )
            ]
        )
        print(f"✅ Created agent: {agent_state.name} (ID: {agent_state.id})")
    except Exception as e:
        print(f"❌ Error creating Letta agent: {e}")
        return
    
    try:
        # Process all questions using utils iterator
        for prompt, metadata in dataset_mgr.get_evaluation_iterator("Letta", model_name, continue_run, existing_file):
            # ONLY framework-specific part: model inference
            try:
                response = client.agents.messages.create(
                    agent_id=agent_state.id,
                    messages=[
                        MessageCreate(
                            role="user",
                            content=prompt
                        )
                    ]
                )
                
                raw_agent_output = extract_agent_response(response)
                if not raw_agent_output:
                    raw_agent_output = "ERROR: Empty response from Letta agent"
            except Exception as e:
                raw_agent_output = f"MODEL_ERROR: {e}"
            
            # Let utils handle result processing
            dataset_mgr.process_result(raw_agent_output, metadata)
    
    finally:
        # Clean up agent
        try:
            print(f"🧹 Cleaning up agent: {agent_state.id}")
            client.agents.delete(agent_id=agent_state.id)
            print("✅ Agent cleanup successful")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up agent: {e}")
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("Letta")


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
    
    print(f"Running Letta {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)