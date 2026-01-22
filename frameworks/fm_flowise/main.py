import json
import os
import sys
import time
import subprocess
import signal
import atexit
import requests
from datetime import datetime
from pathlib import Path

from datasets import load_dataset
from flowise import Flowise, PredictionData

# Import shared utilities
sys.path.append('..')
from utils import (
    bbh_task_names, N_SHOTS, ENABLE_COT, 
    format_bbh_prompt, extract_answer, 
    get_target_classes_and_datatype, prepare_few_shot_examples,
    ensure_openai_api_key
)


# Global variable to track Flowise server process
flowise_process = None
chatflow_id = None


def cleanup_flowise():
    """Clean up Flowise server process on exit."""
    global flowise_process
    if flowise_process:
        print("🛑 Stopping Flowise server...")
        try:
            flowise_process.terminate()
            flowise_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            flowise_process.kill()
        except:
            pass


def start_flowise_server():
    """Start Flowise server and wait for it to be ready."""
    global flowise_process
    
    print("🚀 Starting Flowise server...")
    
    # Start Flowise server using local installation with port 3010
    flowise_process = subprocess.Popen(
        ["bunx", "flowise", "start", "--PORT", "3010"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Register cleanup function
    atexit.register(cleanup_flowise)
    
    # Wait for server to be ready (check if port 3010 is accessible)
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:3010", timeout=5)
            if response.status_code == 200:
                print("✅ Flowise server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"⏳ Waiting for Flowise server... ({i+1}/{max_retries})")
        time.sleep(2)
    
    print("❌ Failed to start Flowise server")
    return False


def create_simple_chatflow():
    """Create a simple chatflow programmatically via API."""
    global chatflow_id
    
    print("🔧 Creating simple chatflow...")
    
    # Simple chatflow configuration using OpenAI
    chatflow_config = {
        "nodes": [
            {
                "width": 300,
                "height": 143,
                "id": "openAI_0",
                "position": {"x": 842.5694259096533, "y": 196.09175134276532},
                "type": "customNode",
                "data": {
                    "id": "openAI_0",
                    "label": "OpenAI",
                    "version": 4,
                    "name": "openAI",
                    "type": "OpenAI",
                    "baseClasses": ["OpenAI", "BaseLLM", "BaseLanguageModel"],
                    "category": "LLMs",
                    "description": "Wrapper around OpenAI large language models",
                    "inputParams": [
                        {"label": "Connect Credential", "name": "credential", "type": "credential", "credentialNames": ["openAIApi"]},
                        {"label": "Model Name", "name": "modelName", "type": "options", "options": [{"label": "gpt-4.1-nano", "name": "gpt-4.1-nano"}], "default": "gpt-4.1-nano"},
                        {"label": "Temperature", "name": "temperature", "type": "number", "step": 0.1, "default": 0.9},
                        {"label": "Max Tokens", "name": "maxTokens", "type": "number", "step": 1},
                        {"label": "Top Probability", "name": "topP", "type": "number", "step": 0.1},
                        {"label": "Frequency Penalty", "name": "frequencyPenalty", "type": "number", "step": 0.1},
                        {"label": "Presence Penalty", "name": "presencePenalty", "type": "number", "step": 0.1},
                        {"label": "Timeout", "name": "timeout", "type": "number", "step": 1},
                        {"label": "BasePath", "name": "basepath", "type": "string"}
                    ],
                    "inputAnchors": [],
                    "inputs": {"modelName": "gpt-4.1-nano", "temperature": 0.9},
                    "outputAnchors": [{"id": "openAI_0-output-openAI-OpenAI|BaseLLM|BaseLanguageModel", "name": "openAI", "label": "OpenAI", "type": "OpenAI | BaseLLM | BaseLanguageModel"}]
                }
            },
            {
                "width": 300,
                "height": 329,
                "id": "conversationChain_0",
                "position": {"x": 1192.0243596088522, "y": 129.2998619164823},
                "type": "customNode",
                "data": {
                    "id": "conversationChain_0",
                    "label": "Conversation Chain",
                    "version": 1,
                    "name": "conversationChain",
                    "type": "ConversationChain",
                    "baseClasses": ["ConversationChain", "BaseChain"],
                    "category": "Chains",
                    "description": "Chat models taking a list of messages as input",
                    "inputParams": [
                        {"label": "System Message", "name": "systemMessagePrompt", "type": "string", "rows": 4, "placeholder": "You are a helpful assistant that answers questions accurately."},
                        {"label": "Chain Option", "name": "chainOption", "type": "options", "options": [{"label": "MapReduceDocumentsChain", "name": "map_reduce"}, {"label": "RefineDocumentsChain", "name": "refine"}, {"label": "StuffDocumentsChain", "name": "stuff"}], "default": "stuff"}
                    ],
                    "inputAnchors": [
                        {"label": "Language Model", "name": "model", "type": "BaseLanguageModel"},
                        {"label": "Memory", "name": "memory", "type": "BaseMemory"}
                    ],
                    "inputs": {"model": "{{openAI_0.data.instance}}", "systemMessagePrompt": "You are an expert problem solver. Answer questions accurately and show your reasoning clearly."},
                    "outputAnchors": [{"id": "conversationChain_0-output-conversationChain-ConversationChain|BaseChain", "name": "conversationChain", "label": "ConversationChain", "type": "ConversationChain | BaseChain"}]
                }
            }
        ],
        "edges": [
            {"source": "openAI_0", "sourceHandle": "openAI_0-output-openAI-OpenAI|BaseLLM|BaseLanguageModel", "target": "conversationChain_0", "targetHandle": "conversationChain_0-input-model-BaseLanguageModel", "type": "buttonedge", "id": "openAI_0-openAI_0-output-openAI-OpenAI|BaseLLM|BaseLanguageModel-conversationChain_0-conversationChain_0-input-model-BaseLanguageModel"}
        ]
    }
    
    try:
        # Create chatflow via API
        response = requests.post(
            "http://localhost:3010/api/v1/chatflows",
            json={
                "name": "BBH Solver",
                "flowData": json.dumps(chatflow_config),
                "deployed": True,
                "isPublic": True,
                "apikeyid": "",
                "chatbotConfig": {}
            },
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            chatflow_id = result.get('id')
            print(f"✅ Created chatflow with ID: {chatflow_id}")
            return chatflow_id
        else:
            print(f"❌ Failed to create chatflow: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating chatflow: {e}")
        return None


def create_results_file(sample_mode, timestamp):
    """Create initial results file structure."""
    os.makedirs("outputs", exist_ok=True)
    
    filename = f"outputs/flowise_bbh_{'first3tasks' if sample_mode else 'full'}_{timestamp}.json"
    
    tasks_to_run = bbh_task_names[:3] if sample_mode else bbh_task_names
    
    initial_results = {
        'framework': 'Flowise',
        'model': 'gpt-4.1-nano',
        'mode': f"sample_first_3_tasks" if sample_mode else "full",
        'tasks_run': len(tasks_to_run),
        'tasks_list': tasks_to_run,
        'timestamp': timestamp,
        'status': 'running',
        'current_task': '',
        'overall_accuracy': 0.0,
        'total_questions': 0,
        'correct_answers': 0,
        'detailed_results': []
    }
    
    with open(filename, 'w') as f:
        json.dump(initial_results, f, indent=2)
    
    return filename


def save_progress(filename, results_data):
    """Save current progress to file."""
    with open(filename, 'w') as f:
        json.dump(results_data, f, indent=2)


def load_existing_results(filename):
    """Load existing results and determine where to continue."""
    try:
        with open(filename, 'r') as f:
            results = json.load(f)
        
        # Find completed tasks
        completed_tasks = set()
        completed_questions = {}
        
        for result in results['detailed_results']:
            task = result['task']
            completed_tasks.add(task)
            if task not in completed_questions:
                completed_questions[task] = 0
            completed_questions[task] += 1
        
        return results, completed_tasks, completed_questions
    except:
        return None, set(), {}


def run_benchmark(sample_mode=True, continue_run=False, existing_file=None):
    """Run the BBH benchmark using Flowise."""
    global chatflow_id
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Handle continue mode
    if continue_run and existing_file:
        print(f"📂 Continuing from: {existing_file}")
        results_data, completed_tasks, completed_questions = load_existing_results(existing_file)
        if not results_data:
            print("❌ Could not load existing results file")
            return
        filename = existing_file
        
        # Extract chatflow_id from previous run if available
        if 'chatflow_id' in results_data:
            chatflow_id = results_data['chatflow_id']
    else:
        # Create new results file
        filename = create_results_file(sample_mode, timestamp)
        results_data = json.loads(open(filename).read())
        completed_tasks = set()
        completed_questions = {}
    
    print(f"📁 Results file: {filename}")
    
    # Start Flowise server if not already running
    if not chatflow_id:
        if not start_flowise_server():
            print("❌ Failed to start Flowise server")
            return
        
        # Create chatflow
        chatflow_id = create_simple_chatflow()
        if not chatflow_id:
            print("❌ Failed to create chatflow")
            cleanup_flowise()
            return
        
        # Store chatflow_id in results for continuation
        results_data['chatflow_id'] = chatflow_id
        save_progress(filename, results_data)
    
    # Ensure OpenAI API key is available (needed for Flowise workflows)
    ensure_openai_api_key()
    # Create Flowise client
    client = Flowise(base_url="http://localhost:3010")
    
    tasks_to_run = bbh_task_names[:3] if sample_mode else bbh_task_names
    
    for task_name in tasks_to_run:
        print(f"\n--- Running BBH Task: {task_name} ---")
        
        # Skip if task already completed (in continue mode)
        if continue_run and task_name in completed_tasks:
            existing_count = completed_questions.get(task_name, 0)
            print(f"  ⏭️  Task already completed ({existing_count} questions), skipping...")
            continue
            
        results_data['current_task'] = task_name
        
        try:
            dataset_parts = load_dataset("maveriq/bigbenchhard", task_name)
            test_data = dataset_parts['train']

            target_classes, datatype = get_target_classes_and_datatype(test_data)
            few_shot_examples = prepare_few_shot_examples(test_data, N_SHOTS)
                
            print(f"  Target classes: {target_classes[:5]}{'...' if len(target_classes) > 5 else ''} (datatype: {datatype})")
            
        except Exception as e:
            print(f"  Error loading task {task_name}: {e}. Skipping.")
            continue

        task_correct_count = 0
        task_total_count = 0
        
        # Use only 3 samples in sample mode
        data_to_process = list(test_data)[:3] if sample_mode else test_data
        
        # Skip already processed questions in continue mode
        start_idx = completed_questions.get(task_name, 0) if continue_run else 0

        for i, item in enumerate(data_to_process[start_idx:], start=start_idx):
            question = item['input']
            target_answer = str(item['target']).strip()

            prompt_for_agent = format_bbh_prompt(question, few_shot_examples, ENABLE_COT)

            try:
                # Get agent response using Flowise
                prediction = client.create_prediction(
                    PredictionData(
                        chatflowId=chatflow_id,
                        question=prompt_for_agent,
                        streaming=False
                    )
                )
                
                # Extract agent's text response from Flowise prediction
                agent_raw_output = ""
                for response in prediction:
                    if hasattr(response, 'text'):
                        agent_raw_output += response.text
                    elif isinstance(response, dict) and 'text' in response:
                        agent_raw_output += response['text']
                    else:
                        agent_raw_output += str(response)

                extracted_answer = extract_answer(agent_raw_output, target_classes, datatype, question)
                is_correct = (extracted_answer == target_answer) if extracted_answer is not None else False

                result_entry = {
                    'task': task_name,
                    'question_index': i,
                    'question': question,
                    'raw_agent_output': agent_raw_output,
                    'extracted_answer': extracted_answer,
                    'target_answer': target_answer,
                    'target_classes': target_classes,
                    'datatype': datatype,
                    'is_correct': is_correct
                }
                
                # Add to results and save immediately
                results_data['detailed_results'].append(result_entry)
                results_data['total_questions'] = len(results_data['detailed_results'])
                results_data['correct_answers'] = sum(1 for r in results_data['detailed_results'] if r['is_correct'])
                results_data['overall_accuracy'] = (results_data['correct_answers'] / results_data['total_questions']) * 100
                
                save_progress(filename, results_data)

                task_total_count += 1
                if is_correct:
                    task_correct_count += 1

                status = '✅ Correct' if is_correct else ('❌ Failed extraction' if extracted_answer is None else '❌ Incorrect')
                print(f"  Q {i+1} Result: {status}")

            except Exception as e:
                print(f"  Error during agent processing for Q {i+1} ({task_name}): {e}")
                
                error_entry = {
                    'task': task_name, 'question_index': i, 'question': question, 
                    'raw_agent_output': f"ERROR: {e}",
                    'extracted_answer': None, 'target_answer': target_answer, 
                    'target_classes': target_classes, 'datatype': datatype, 'is_correct': False
                }
                
                results_data['detailed_results'].append(error_entry)
                results_data['total_questions'] = len(results_data['detailed_results'])
                results_data['correct_answers'] = sum(1 for r in results_data['detailed_results'] if r['is_correct'])
                results_data['overall_accuracy'] = (results_data['correct_answers'] / results_data['total_questions']) * 100
                
                save_progress(filename, results_data)
                task_total_count += 1

        task_accuracy = (task_correct_count / task_total_count) * 100 if task_total_count > 0 else 0
        print(f"  {task_name} Accuracy: {task_accuracy:.2f}% ({task_correct_count}/{task_total_count})")
    
    # Mark as completed
    results_data['status'] = 'completed'
    results_data['current_task'] = ''
    save_progress(filename, results_data)
    
    print(f"\n📊 Overall Accuracy: {results_data['overall_accuracy']:.2f}%")
    print(f"📁 Results saved to: {filename}")
    
    # Cleanup Flowise server
    cleanup_flowise()
    
    return results_data


def find_latest_results_file():
    """Find the most recent results file for continuation."""
    output_dir = Path("outputs")
    if not output_dir.exists():
        return None
    
    json_files = list(output_dir.glob("flowise_bbh_*.json"))
    if not json_files:
        return None
    
    # Sort by modification time, return most recent
    latest = max(json_files, key=lambda f: f.stat().st_mtime)
    return str(latest)


if __name__ == "__main__":
    # Parse arguments
    sample_mode = "--full" not in sys.argv
    continue_run = "--continue" in sys.argv
    
    existing_file = None
    if continue_run:
        existing_file = find_latest_results_file()
        if not existing_file:
            print("❌ No existing results file found to continue from")
            sys.exit(1)
        print(f"📂 Found existing file: {existing_file}")
    
    print(f"Running Flowise BBH Benchmark ({'First 3 tasks' if sample_mode else 'All tasks'})")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_benchmark(sample_mode, continue_run, existing_file)