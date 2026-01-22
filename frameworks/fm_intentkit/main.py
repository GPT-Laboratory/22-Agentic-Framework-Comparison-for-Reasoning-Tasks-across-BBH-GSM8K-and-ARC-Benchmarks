import os
import sys
import time
import requests

from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager


def call_intentkit_api(base_url, endpoint, method="GET", payload=None):
    """Call IntentKit API endpoints."""
    url = f"{base_url}{endpoint}"
    
    try:
        if method == "POST":
            response = requests.post(url, json=payload, timeout=60)
        else:
            response = requests.get(url, timeout=60)
            
        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"API failed: {response.status_code} - {response.text}")
    except Exception as e:
        raise Exception(f"API error: {e}")


def create_intentkit_agent(base_url, system_prompt):
    """Create a reasoning agent for dataset tasks."""
    agent_config = {
        "name": f"dataset_agent_{int(time.time())}",
        "type": "reasoning",
        "description": "Agent for dataset benchmarking tasks",
        "system_prompt": system_prompt,
        "capabilities": ["reasoning", "text_processing"],
        "config": {
            "model": "gpt-4.1-mini",
            "temperature": 0.0,
            "max_tokens": 1000
        }
    }
    
    try:
        agent = call_intentkit_api(base_url, "/agents", "POST", agent_config)
        return agent.get("id") or agent.get("agent_id")
    except Exception as e:
        alternative_endpoints = ["/api/agents", "/v1/agents", "/create_agent"]
        for endpoint in alternative_endpoints:
            try:
                agent = call_intentkit_api(base_url, endpoint, "POST", agent_config)
                return agent.get("id") or agent.get("agent_id")
            except:
                continue
        
        raise Exception(f"Failed to create agent: {e}")


def chat_with_agent(base_url, agent_id, prompt):
    """Send a prompt to the agent and get response."""
    
    try:
        import urllib.parse
        query_params = urllib.parse.urlencode({"q": prompt})
        debug_url = f"{base_url}/debug/{agent_id}/chat?{query_params}"
        
        response = requests.get(debug_url, timeout=60)
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    
    try:
        chat_payload = {
            "message": prompt,
            "chat_id": f"chat_{int(time.time())}"
        }
        response = call_intentkit_api(base_url, f"/agents/{agent_id}/chat/v2", "POST", chat_payload)
        
        if isinstance(response, list) and len(response) > 0:
            last_message = response[-1]
            if isinstance(last_message, dict):
                return (last_message.get("message") or 
                       last_message.get("content") or 
                       last_message.get("text") or
                       str(last_message))
        
        return str(response)
    except Exception:
        pass
    
    try:
        chat_payload = {
            "message": prompt,
            "chat_id": f"chat_{int(time.time())}"
        }
        response = call_intentkit_api(base_url, f"/agents/{agent_id}/chat", "POST", chat_payload)
        
        if isinstance(response, dict):
            return (response.get("message") or 
                   response.get("content") or 
                   response.get("text") or
                   response.get("response") or
                   str(response))
        
        return str(response)
    except Exception:
        pass
    
    raise Exception("Failed to get response from agent")


def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using IntentKit with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Initialize IntentKit - ONLY framework-specific part
    print("🔧 Initializing IntentKit agent...")
    system_prompt = dataset_mgr.get_system_prompt()
    intentkit_url = os.getenv('INTENTKIT_URL', 'http://localhost:8000')

    try:
        health_response = requests.get(f"{intentkit_url}/health", timeout=10)
        if health_response.status_code != 200:
            raise Exception(f"IntentKit server not accessible: {health_response.status_code}")
    except Exception as e:
        raise Exception(f"IntentKit server error: {e}")

    agent_id = create_intentkit_agent(intentkit_url, system_prompt)
    print(f"✅ Agent created: {agent_id}")
    
    # Process all questions using utils iterator
    for prompt, metadata in dataset_mgr.get_evaluation_iterator("IntentKit", "gpt-4.1-mini", continue_run, existing_file):
        # ONLY framework-specific part: model inference
        try:
            raw_agent_output = chat_with_agent(intentkit_url, agent_id, prompt)
            
            if not raw_agent_output or raw_agent_output == 'None':
                raw_agent_output = "MODEL_ERROR: Empty response from IntentKit agent"
        except Exception as e:
            raw_agent_output = f"MODEL_ERROR: {e}"
        
        # Let utils handle result processing
        dataset_mgr.process_result(raw_agent_output, metadata)
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("IntentKit")


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
    
    print(f"Running IntentKit {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)