import sys
import openai

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


class Agent:
    """Minimal ANUS Agent implementation using OpenAI API directly."""

    def __init__(self, system_prompt: str = None, model: str = "gpt-4.1-mini"):
        self.model = model
        self.client = openai.OpenAI()

        # Use provided system prompt or default
        if system_prompt:
            self.instructions = system_prompt
        else:
            self.instructions = "You are an expert problem solver. Answer questions accurately and show your reasoning clearly."
    
    def run(self, prompt: str) -> str:
        """Execute the agent with the given prompt."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.1,
                timeout=60
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"MODEL_ERROR: {e}"


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using ANUS with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Initialize ANUS agent - ONLY framework-specific part
    print("🔧 Initializing ANUS agent...")
    system_prompt = dataset_mgr.get_system_prompt()
    agent = Agent(system_prompt=system_prompt, model="gpt-4.1-mini")
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("ANUS", "gpt-4.1-mini", continue_run, existing_file):
        # ONLY framework-specific part: agent inference
        raw_agent_output = agent.run(prompt)
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("ANUS")


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
    
    print(f"Running ANUS {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)