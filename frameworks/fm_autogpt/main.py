import sys

# AutoGPT Forge SDK imports
from forge.sdk import Agent, AgentDB, Task, TaskRequestBody, Step, StepRequestBody
from forge.sdk.workspace import LocalWorkspace
from forge.llm import chat_completion_request

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


class AutoGPTAgent(Agent):
    """AutoGPT agent using Forge SDK for multi-dataset tasks."""

    def __init__(self, database: AgentDB, workspace: LocalWorkspace, system_prompt: str = None):
        super().__init__(database, workspace)
        self.system_prompt = system_prompt or "You are an expert reasoning agent specialized in solving complex logical and mathematical problems."
        
    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute a single problem solving step."""
        # Get the task this step is for
        task = await self.db.get_task(task_id)
        
        # Create a new step in the database
        step = await self.db.create_step(
            task_id=task_id, input=step_request, is_last=True
        )
        
        # Get the problem text from step input
        problem_text = step_request.input
        
        # Use AutoGPT's chat completion with centralized system prompt
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": problem_text}
        ]
        
        try:
            # Make chat completion request using AutoGPT's method
            chat_response = await chat_completion_request(
                messages=messages,
                model="gpt-4.1-mini",
            )
            
            # Extract response text
            agent_output = chat_response.choices[0].message.content
            
        except Exception as e:
            agent_output = f"MODEL_ERROR: {e}"
        
        # Set the step output 
        step.output = agent_output
        
        return step


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using AutoGPT with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Initialize AutoGPT components - ONLY framework-specific part
    print("🔧 Initializing AutoGPT agent...")
    system_prompt = dataset_mgr.get_system_prompt()
    db = AgentDB("sqlite:///agent.db")
    workspace = LocalWorkspace("./workspace")
    agent = AutoGPTAgent(db, workspace, system_prompt)
    
    # Process all questions using utils iterator
    async def process_questions():
        for prompt, metadata in dataset_mgr.get_evaluation_iterator("AutoGPT", "gpt-4.1-mini", continue_run, existing_file):
            # ONLY framework-specific part: model inference
            try:
                # Create a task for AutoGPT agent
                task_request = TaskRequestBody(input=prompt)
                task = await agent.create_task(task_request)
                
                # Execute the step
                step_request = StepRequestBody(input=prompt)
                step = await agent.execute_step(task.task_id, step_request)
                
                # Get the agent's response
                raw_agent_output = step.output
                
            except Exception as e:
                raw_agent_output = f"MODEL_ERROR: {e}"
            
            # Let utils handle result processing
            dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Run the async processing
    import asyncio
    asyncio.run(process_questions())
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("AutoGPT")


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
    
    print(f"Running AutoGPT {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)