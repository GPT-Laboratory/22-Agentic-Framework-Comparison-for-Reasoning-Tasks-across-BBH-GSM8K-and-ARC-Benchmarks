import asyncio
import sys
from livekit.plugins import openai as lk_openai
from livekit.agents import llm

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


class LiveKitWrapper:
    """Synchronous wrapper for LiveKit LLM."""

    def __init__(self, model_name="gpt-4.1-mini", system_prompt=None):
        self.llm = lk_openai.LLM(model=model_name, temperature=0.0)
        self.system_prompt = system_prompt
        self.loop = None
    
    def _ensure_loop(self):
        """Ensure we have a running event loop."""
        if self.loop is None or self.loop.is_closed():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    async def _generate_async(self, prompt):
        """Generate response using LiveKit LLM asynchronously."""
        chat_ctx = llm.ChatContext()
        if self.system_prompt:
            chat_ctx.add_message(role="system", content=self.system_prompt)
        chat_ctx.add_message(role="user", content=prompt)
        
        response_chunks = []
        async for chunk in self.llm.chat(chat_ctx=chat_ctx):
            if chunk.delta and chunk.delta.content:
                response_chunks.append(chunk.delta.content)
        
        return ''.join(response_chunks)
    
    def generate_response(self, prompt):
        """Generate synchronous response using LiveKit LLM."""
        self._ensure_loop()
        try:
            return self.loop.run_until_complete(self._generate_async(prompt))
        except Exception as e:
            # If there's an event loop issue, try with a fresh loop
            if "Event loop is closed" in str(e) or "RuntimeError" in str(e):
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                return self.loop.run_until_complete(self._generate_async(prompt))
            else:
                raise e
    
    def close(self):
        """Properly close the event loop."""
        if self.loop and not self.loop.is_closed():
            self.loop.close()


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using LiveKit with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Get system prompt from dataset manager
    system_prompt = dataset_mgr.get_system_prompt()

    # Initialize LiveKit model - ONLY framework-specific part
    print("🔧 Initializing LiveKit model...")
    model = LiveKitWrapper("gpt-4.1-mini", system_prompt=system_prompt)
    
    try:
        # Process all questions using utils iterator
        for prompt, metadata in dataset_mgr.get_evaluation_iterator("LiveKit", "gpt-4.1-mini", continue_run, existing_file):
            # ONLY framework-specific part: model inference
            try:
                raw_agent_output = model.generate_response(prompt)
            except Exception as e:
                raw_agent_output = f"MODEL_ERROR: {e}"
            
            # Let utils handle result processing
            dataset_mgr.process_result(raw_agent_output, metadata)
        
        # Let utils finalize everything
        return dataset_mgr.finalize_evaluation()
    finally:
        # Always close the model properly
        model.close()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("LiveKit")


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
    
    print(f"Running LiveKit {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)