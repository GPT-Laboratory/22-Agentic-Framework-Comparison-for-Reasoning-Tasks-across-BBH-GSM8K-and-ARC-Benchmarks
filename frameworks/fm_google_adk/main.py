import sys
import asyncio

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


async def create_google_adk_agent(system_prompt):
    """Initialize Google ADK agent with proper configuration."""
    try:
        from google.adk.agents import Agent
        from google.adk.models.lite_llm import LiteLlm
        from google.adk.runners import InMemoryRunner
        from google.genai import types

        # Create LiteLLM model instance
        model = LiteLlm(model="gpt-4.1-mini")

        # Create agent with reasoning instructions
        agent = Agent(
            name="bbh_reasoning_agent",
            model=model,
            instruction=system_prompt,
            description="Agent specialized in solving Big Bench Hard reasoning tasks with step-by-step analysis"
        )

        return agent

    except ImportError as e:
        print(f"❌ Failed to import Google ADK: {e}")
        print("Please ensure google-adk is installed: uv add google-adk")
        sys.exit(1)


async def query_google_adk_agent(agent, prompt):
    """Query the Google ADK agent and return response."""
    try:
        from google.adk.runners import InMemoryRunner
        from google.genai import types
        
        # Create runner
        runner = InMemoryRunner(agent=agent, app_name="bbh_benchmark")
        session_service = runner.session_service
        
        # Create session
        await session_service.create_session(
            app_name="bbh_benchmark",
            user_id="bbh_user", 
            session_id="bbh_session"
        )
        
        # Create content
        content = types.Content(role='user', parts=[types.Part(text=prompt)])
        
        # Run agent and collect response
        final_response = ""
        async for event in runner.run_async(
            user_id="bbh_user",
            session_id="bbh_session",
            new_message=content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
                break
        
        return final_response
        
    except Exception as e:
        return f"MODEL_ERROR: {e}"


async def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using Google ADK with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Initialize Google ADK agent - ONLY framework-specific part
    print("🔧 Initializing Google ADK agent...")
    system_prompt = dataset_mgr.get_system_prompt()
    agent = await create_google_adk_agent(system_prompt)
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("Google ADK", "gpt-4.1-mini", continue_run, existing_file):
        # ONLY framework-specific part: model inference
        raw_agent_output = await query_google_adk_agent(agent, prompt)
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("Google ADK")


async def main():
    """Main async entry point."""
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
    
    print(f"Running Google ADK {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    await run_evaluation(dataset_name, mode, continue_run, existing_file)


if __name__ == "__main__":
    asyncio.run(main())