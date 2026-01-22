import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import requests

from datasets import load_dataset
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')  # Load N8N configuration

# Import shared utilities
sys.path.append('..')
from utils import (
    bbh_task_names, N_SHOTS, ENABLE_COT, 
    format_bbh_prompt, extract_answer, 
    get_target_classes_and_datatype, prepare_few_shot_examples
)


def call_n8n_webhook(webhook_url, prompt, model="gpt-4.1-nano"):
    """Call the N8N webhook with a prompt."""
    payload = {
        "prompt": prompt,
        "model": model,
        "request_id": f"bbh_{int(time.time())}"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Webhook failed: {response.status_code} - {response.text}")
    except Exception as e:
        raise Exception(f"Webhook error: {e}")


def create_results_file(sample_mode, timestamp):
    """Create initial results file structure."""
    os.makedirs("outputs", exist_ok=True)
    
    filename = f"outputs/n8n_bbh_{'first3tasks' if sample_mode else 'full'}_{timestamp}.json"
    
    tasks_to_run = bbh_task_names[:3] if sample_mode else bbh_task_names
    
    initial_results = {
        'framework': 'N8N',
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
    """Run the BBH benchmark using N8N workflows."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Check for required environment variables
    n8n_url = os.getenv('N8N_URL', 'http://localhost:5678')
    n8n_webhook_path = os.getenv('N8N_WEBHOOK_PATH')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not n8n_webhook_path:
        print("❌ Error: N8N_WEBHOOK_PATH not found in .env.local")
        print("   Please run ./setup.sh first to configure the N8N workflow")
        return
        
    if not openai_api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("   Please run ./setup.sh first to configure the environment")
        return
    
    # Build webhook URL
    webhook_url = f"{n8n_url}/webhook/{n8n_webhook_path}"
    
    # Test N8N connectivity
    print(f"🔍 Testing N8N webhook at {webhook_url}...")
    try:
        test_payload = {"prompt": "test", "model": "gpt-4.1-nano"}
        test_response = requests.post(webhook_url, json=test_payload, timeout=10)
        if test_response.status_code == 200:
            print("✅ N8N webhook is accessible")
        else:
            print(f"⚠️ N8N webhook returned status {test_response.status_code}, but continuing...")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Could not reach N8N webhook: {e}")
        print("   Make sure N8N is running and configured. Run: docker compose up -d")
        return
    
    # Handle continue mode
    if continue_run and existing_file:
        print(f"📂 Continuing from: {existing_file}")
        results_data, completed_tasks, completed_questions = load_existing_results(existing_file)
        if not results_data:
            print("❌ Could not load existing results file")
            return
        filename = existing_file
    else:
        # Create new results file
        filename = create_results_file(sample_mode, timestamp)
        results_data = json.loads(open(filename).read())
        completed_tasks = set()
        completed_questions = {}
    
    print(f"📁 Results file: {filename}")
    
    tasks_to_run = bbh_task_names[:3] if sample_mode else bbh_task_names
    
    for task_name in tasks_to_run:
        print(f"\\n--- Running BBH Task: {task_name} ---")
        
        # Skip if task already completed (in continue mode)
        if continue_run and task_name in completed_tasks:
            existing_count = completed_questions.get(task_name, 0)
            print(f"  ⏭️ Task already completed ({existing_count} questions), skipping...")
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
                print(f"  🚀 Executing via N8N webhook...")
                
                # Call the N8N webhook
                response = call_n8n_webhook(webhook_url, prompt_for_agent)
                
                # Extract the agent output
                if isinstance(response, list) and len(response) > 0:
                    agent_raw_output = response[0].get('output', '')
                else:
                    agent_raw_output = str(response)
                
                if not agent_raw_output or agent_raw_output == 'None':
                    raise Exception("Empty response from N8N webhook")

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
                print(f"  Error during N8N processing for Q {i+1} ({task_name}): {e}")
                
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
    
    print(f"\\n📊 Overall Accuracy: {results_data['overall_accuracy']:.2f}%")
    print(f"📁 Results saved to: {filename}")
    
    return results_data


def find_latest_results_file():
    """Find the most recent results file for continuation."""
    output_dir = Path("outputs")
    if not output_dir.exists():
        return None
    
    json_files = list(output_dir.glob("n8n_bbh_*.json"))
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
    
    print(f"Running N8N BBH Benchmark ({'First 3 tasks' if sample_mode else 'All tasks'})")
    if continue_run:
        print("🔄 Continue mode enabled")
    print("=" * 50)
    
    run_benchmark(sample_mode, continue_run, existing_file)