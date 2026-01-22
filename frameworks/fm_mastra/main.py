import sys
import os
import subprocess
import signal
import requests
import time

# Import ultra-clean dataset utilities
sys.path.append('..')
from utils import DatasetManager

# Global variable for server process
agent_server_process = None

def start_mastra_server():
    """Start the Mastra agent server."""
    global agent_server_process
    
    # Find available port
    import socket
    for port in range(3000, 3100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                break
            except OSError:
                continue
    else:
        raise Exception("No available ports found")
    
    # Set environment and start server
    env = os.environ.copy()
    env['MASTRA_PORT'] = str(port)
    
    agent_server_process = subprocess.Popen(
        ['node', 'agent-server.js'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=os.setsid
    )
    
    # Wait for server ready
    start_time = time.time()
    while time.time() - start_time < 30:
        try:
            response = requests.get(f'http://127.0.0.1:{port}/health', timeout=2)
            if response.status_code == 200:
                return port
        except requests.RequestException:
            pass
        time.sleep(1)
    
    raise Exception("Server failed to start")

def cleanup_server():
    """Clean up the agent server process."""
    global agent_server_process
    if agent_server_process:
        try:
            os.killpg(os.getpgid(agent_server_process.pid), signal.SIGTERM)
            agent_server_process.wait(timeout=10)
        except:
            try:
                os.killpg(os.getpgid(agent_server_process.pid), signal.SIGKILL)
                agent_server_process.wait()
            except:
                pass
        agent_server_process = None

def call_mastra_agent(prompt, port, system_prompt=None):
    """Call the Mastra agent with a prompt."""
    payload = {"prompt": prompt}
    if system_prompt:
        payload["system_prompt"] = system_prompt

    response = requests.post(
        f'http://127.0.0.1:{port}/solve',
        json=payload,
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return data['answer']
        else:
            raise Exception(f"Agent error: {data.get('error', 'Unknown error')}")
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text}")

def run_evaluation(dataset_name="bbh", mode="sample", continue_run=False, existing_file=None):
    """Run evaluation using Mastra with ultra-clean modular system."""
    
    # Initialize dataset manager with new config
    dataset_mgr = DatasetManager(dataset_name, mode)
    print(f"📋 Dataset: {dataset_mgr.dataset_config['name']} ({mode} mode)")

    # Get system prompt from dataset manager
    system_prompt = dataset_mgr.get_system_prompt()

    # Initialize Mastra server - ONLY framework-specific part
    print("🔧 Initializing Mastra server...")
    port = start_mastra_server()
    print(f"✓ Mastra server ready on port {port}")
    
    try:
        # Process all questions using utils iterator
        for prompt, metadata in dataset_mgr.get_evaluation_iterator("Mastra", "gpt-4.1-mini", continue_run, existing_file):
            # ONLY framework-specific part: model inference
            try:
                raw_agent_output = call_mastra_agent(prompt, port, system_prompt)
            except Exception as e:
                raw_agent_output = f"MODEL_ERROR: {e}"
            
            # Let utils handle result processing
            dataset_mgr.process_result(raw_agent_output, metadata)
    
    finally:
        cleanup_server()
    
    # Let utils finalize everything
    return dataset_mgr.finalize_evaluation()


def find_latest_results_file(dataset_name="bbh", mode="sample"):
    """Find the most recent results file for continuation."""
    dataset_mgr = DatasetManager(dataset_name, mode)
    return dataset_mgr.find_latest_results_file("Mastra")


def signal_handler(signum, frame):
    """Handle termination signals."""
    cleanup_server()
    sys.exit(1)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
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
    
    print(f"Running Mastra {dataset_name.upper()} Evaluation ({'Full' if mode == 'full' else 'Sample'} mode)")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_evaluation(dataset_name, mode, continue_run, existing_file)