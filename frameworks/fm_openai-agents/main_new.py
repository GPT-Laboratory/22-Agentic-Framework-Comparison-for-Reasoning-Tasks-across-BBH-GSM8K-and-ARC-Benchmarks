"""
OpenAI Agents Framework Integration for Universal Benchmarking System

Updated implementation using the new universal benchmarking system that supports
BBH, GSM8K, and ARC datasets. Uses the original OpenAI Agents SDK integration
but with the new dataset-agnostic interface.

Key features:
- Supports multiple datasets (BBH, GSM8K, ARC) 
- Configuration-driven evaluation
- Uses shared dataset handlers for consistency
- Maintains existing OpenAI Agents SDK integration
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Import shared utilities (new system)
sys.path.append('..')
from utils_new import UniversalBenchmarkManager, setup_environment, run_universal_benchmark


class OpenAIAgentsIntegration:
    """OpenAI Agents integration for universal benchmarking."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize OpenAI Agents framework.
        
        Args:
            model_name: Model to use (will be determined from config if not provided)
        """
        self.agent = None
        self.runner = None
        self.model_name = model_name
        print(f"    Initializing OpenAI Agents with model: {self.model_name}")
        
        # Setup environment
        setup_environment()
        
        # Initialize agent
        self._setup_agent()
    
    def _setup_agent(self):
        """Setup OpenAI Agents agent and runner."""
        try:
            # Import OpenAI Agents SDK
            from openai_agents.agents import Agent
            from openai_agents.runners import Runner
            
            # Create agent with reasoning-focused instructions
            self.agent = Agent(
                name="universal_benchmark_solver",
                model=self.model_name,
                instructions="""You are an expert problem solver capable of handling various types of questions including:
- Logic and reasoning problems (BBH tasks)
- Grade school math word problems (GSM8K)
- Science questions with multiple choice answers (ARC)

For each problem:
1. Read the question carefully
2. Think through the solution step by step
3. Provide a clear, direct answer

For math problems: Show your work and end with the numerical answer.
For multiple choice: Select the best option and clearly state your choice (A, B, C, or D).
For reasoning problems: Explain your logic and provide the final answer.
"""
            )
            
            # Create runner
            self.runner = Runner()
            print("    OpenAI Agents initialized successfully")
            
        except ImportError as e:
            print(f"    Error: OpenAI Agents SDK not available: {e}")
            print(f"    Please install: pip install openai-agents")
            raise
        except Exception as e:
            print(f"    Error initializing OpenAI Agents: {e}")
            raise
    
    def run_sync(self, prompt: str) -> str:
        """
        Run agent synchronously and return response.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Agent response text
        """
        try:
            # Run the agent with the prompt
            result = self.runner.run_sync(
                agent=self.agent,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract text response
            if result and hasattr(result, 'messages') and result.messages:
                # Get the last assistant message
                for message in reversed(result.messages):
                    if hasattr(message, 'role') and message.role == 'assistant':
                        return message.content
                
                # Fallback: get last message content
                return result.messages[-1].content if result.messages[-1].content else "No response"
            
            return "No response generated"
            
        except Exception as e:
            print(f"    Error running OpenAI Agents: {e}")
            return f"ERROR: {e}"


def run_universal_benchmark() -> dict:
    """
    Run universal benchmark using OpenAI Agents framework.
    
    Returns:
        Dictionary with results for all enabled datasets
    """
    print("\nRunning OpenAI Agents Universal Benchmark")
    print("=" * 50)
    
    # Initialize benchmark manager
    try:
        manager = UniversalBenchmarkManager("../config2.yml")
    except Exception as e:
        print(f"❌ Failed to initialize benchmark manager: {e}")
        return {'error': str(e)}
    
    # Get model for this framework
    model = manager.get_model("fm_openai-agents")
    
    # Initialize OpenAI Agents
    try:
        agents_integration = OpenAIAgentsIntegration(model)
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI Agents: {e}")
        return {'error': str(e)}
    
    # Define agent function
    def agent_fn(prompt: str) -> str:
        return agents_integration.run_sync(prompt)
    
    # Run benchmark across all enabled datasets
    results = manager.run_benchmark(agent_fn, "openai-agents", model)
    
    return results


def main():
    """Main function for command-line usage."""
    print("OpenAI Agents Framework - Universal Benchmarking")
    print("=" * 60)
    
    try:
        results = run_universal_benchmark()
        
        if 'error' in results:
            print(f"❌ Benchmark failed: {results['error']}")
            return 1
        
        print("\n✅ Universal benchmark completed successfully")
        return 0
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())