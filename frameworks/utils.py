"""
Ultra-clean unified multi-dataset utilities.
Uses modular data loaders and new datasets_new.yml structure.
"""

import json
import random
import os
import yaml
import requests
import time
from pathlib import Path
from datetime import datetime
from data_loaders import DATASET_LOADERS


def get_agent_system_prompt():
    """
    Get the standard system prompt for agent initialization across all frameworks.
    This ensures consistent agent behavior unless overridden by specific datasets.
    """
    return "You are an expert problem solver with strong analytical skills who excels at multi-step reasoning tasks. Answer questions accurately and show clear reasoning."


class DatasetManager:
    """
    Ultra-clean unified dataset manager using modular loaders.
    """
    
    def __init__(self, dataset_name, mode="sample", config_file="datasets.yml"):
        """Initialize dataset manager."""
        self.dataset_name = dataset_name.lower()
        self.mode = mode
        self.config = self._load_config(config_file)
        self.dataset_config = self.config['datasets'][self.dataset_name]
        
        # Initialize dataset-specific loader
        loader_class = DATASET_LOADERS.get(self.dataset_name)
        if not loader_class:
            raise ValueError(f"No loader found for dataset: {self.dataset_name}")
        self.loader = loader_class(self.dataset_config)
        
        self._ensure_openai_api_key()

    def get_system_prompt(self):
        """
        Get the effective system prompt for agent initialization.
        Checks for dataset-specific override first, falls back to default.
        """
        override_prompt = self.loader.get_system_prompt_override()
        if override_prompt:
            return override_prompt
        return get_agent_system_prompt()

    def _load_config(self, config_file):
        """Load datasets configuration from YAML file."""
        config_paths = [config_file, f"../{config_file}", Path(__file__).parent / config_file]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
        
        raise ValueError(f"Could not find datasets configuration file: {config_file}")
    
    def _ensure_openai_api_key(self):
        """Discover and set OpenAI API key for extraction agent."""
        if os.getenv("OPENAI_API_KEY"):
            return
        
        # Check local .env.local file
        if os.path.exists(".env.local"):
            with open(".env.local", 'r') as f:
                for line in f:
                    if line.strip().startswith("OPENAI_API_KEY="):
                        key_value = line.split("=", 1)[1].strip().strip('"')
                        os.environ["OPENAI_API_KEY"] = key_value
                        return
        
        # Check project root .env file
        if os.path.exists("../../.env"):
            with open("../../.env", 'r') as f:
                for line in f:
                    if line.strip().startswith("OPENAI_API_KEY="):
                        key_value = line.split("=", 1)[1].strip().strip('"')
                        os.environ["OPENAI_API_KEY"] = key_value
                        return
        
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
    
    def get_tasks_to_run(self):
        """Get list of tasks to run based on dataset and mode configuration."""
        mode_config = self.dataset_config['modes'][self.mode]
        
        if 'task_list' in self.dataset_config:
            all_tasks = self.dataset_config['task_list']
            tasks_count = mode_config['tasks']
            return all_tasks if tasks_count == -1 else all_tasks[:tasks_count]
        else:
            return [self.dataset_name.upper()]
    
    def get_questions_for_task(self, task_name):
        """Get questions for a specific task based on mode configuration."""
        dataset_data = self.loader.load_dataset_data(task_name)
        questions_per_task = self.dataset_config['modes'][self.mode]['questions_per_task']
        return list(dataset_data) if questions_per_task == -1 else list(dataset_data)[:questions_per_task]
    
    def prepare_few_shot_examples(self, dataset_data, n_shots):
        """Prepare few-shot examples from dataset."""
        if n_shots <= 0 or len(dataset_data) <= n_shots:
            return []
        random.seed(42)
        return random.sample(list(dataset_data), min(n_shots, len(dataset_data)))
    
    def find_latest_results_file(self, framework_name):
        """Find the most recent results file for this framework and dataset."""
        import glob
        framework_safe = framework_name.lower().replace(" ", "_")
        pattern = f"outputs/{framework_safe}_{self.dataset_name}_{self.mode}_*.json"
        files = glob.glob(pattern)
        return sorted(files)[-1] if files else None
    
    def get_evaluation_iterator(self, framework_name, model=None, continue_run=False, existing_file=None):
        """Get iterator that yields prompts and metadata for evaluation."""
        self._setup_evaluation_context(framework_name, model, continue_run, existing_file)
        
        for task_name in self.get_tasks_to_run():
            print(f"\\n--- Running Task: {task_name} ---")
            
            # Skip if task already completed (continue mode)
            if continue_run and task_name in self._completed_tasks_info:
                existing_count = self._completed_tasks_info.get(task_name, 0)
                print(f"  ⏭️  Task already completed ({existing_count} questions), skipping...")
                continue
            
            try:
                # Use loader for dataset-specific operations
                dataset_data = self.loader.load_dataset_data(task_name)
                target_classes, datatype = self.loader.get_target_classes_and_datatype(dataset_data)
                print(f"  Target classes: {target_classes[:5]}{'...' if len(target_classes) > 5 else ''} (datatype: {datatype})")
                
                n_shots = self.dataset_config['prompting']['n_shots']
                few_shot_examples = self.prepare_few_shot_examples(dataset_data, n_shots)
            except Exception as e:
                print(f"  Error loading task {task_name}: {e}. Skipping.")
                continue
            
            questions = self.get_questions_for_task(task_name)
            start_idx = self._completed_tasks_info.get(task_name, 0) if continue_run else 0
            
            for i, question_data in enumerate(questions[start_idx:], start=start_idx):
                # Use loader for dataset-specific processing
                target_field = self.dataset_config['target_field']
                raw_target = str(question_data[target_field]).strip()
                target_answer = self.loader.extract_target_answer(raw_target)
                
                enable_cot = self.dataset_config['prompting']['enable_cot']
                prompt = self.loader.format_prompt(question_data, few_shot_examples, enable_cot)
                
                metadata = {
                    'task_name': task_name,
                    'question_index': i,
                    'question_data': question_data,
                    'target_answer': target_answer,
                    'target_classes': target_classes,
                    'datatype': datatype
                }
                
                yield prompt, metadata
    
    def process_result(self, raw_agent_output, metadata):
        """Process a single result from framework inference."""
        try:
            # Use loader for dataset-specific answer extraction
            input_field = self.dataset_config['input_field']
            original_question = metadata['question_data'][input_field] if isinstance(metadata['question_data'], dict) else str(metadata['question_data'])
            
            extracted_answer = self.loader.extract_agent_answer(
                raw_agent_output, 
                metadata['target_classes'], 
                metadata['datatype'], 
                original_question
            )
            
            is_correct = (extracted_answer == metadata['target_answer']) if extracted_answer is not None else False
            
            # Generate metadata if loader supports it
            result_metadata = {}
            if hasattr(self.loader, 'generate_metadata'):
                try:
                    result_metadata = self.loader.generate_metadata(
                        raw_agent_output, 
                        metadata['target_answer'], 
                        original_question
                    )
                except Exception as e:
                    print(f"    Warning: Failed to generate metadata: {e}")
            
            # Add to results file
            self._add_result_to_file(metadata, raw_agent_output, extracted_answer, is_correct, result_metadata)
            
            # Track task progress
            if metadata['task_name'] not in self._task_stats:
                self._task_stats[metadata['task_name']] = {'correct': 0, 'total': 0}
            
            self._task_stats[metadata['task_name']]['total'] += 1
            if is_correct:
                self._task_stats[metadata['task_name']]['correct'] += 1
            
            status = '✅ Correct' if is_correct else ('❌ Failed extraction' if extracted_answer is None else '❌ Incorrect')
            print(f"  Q {metadata['question_index']+1} Result: {status}")
            
        except Exception as e:
            print(f"  Error processing Q {metadata['question_index']+1}: {e}")
            self._add_result_to_file(metadata, f"ERROR: {e}", None, False, None)
            
            if metadata['task_name'] not in self._task_stats:
                self._task_stats[metadata['task_name']] = {'correct': 0, 'total': 0}
            self._task_stats[metadata['task_name']]['total'] += 1
    
    def finalize_evaluation(self):
        """Finalize the evaluation and return results."""
        for task_name, stats in self._task_stats.items():
            task_accuracy = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"  {task_name} Accuracy: {task_accuracy:.2f}% ({stats['correct']}/{stats['total']})")
        
        # Update final status
        with open(self._results_filename, 'r') as f:
            results_data = json.load(f)
        
        results_data['status'] = 'completed'
        results_data['completion_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self._results_filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\\n📊 Overall Accuracy: {results_data['overall_accuracy']:.2f}%")
        print(f"📁 Results saved to: {self._results_filename}")
        
        return results_data
    
    def _setup_evaluation_context(self, framework_name, model, continue_run, existing_file):
        """Setup evaluation context and state."""
        if continue_run and existing_file:
            print(f"📂 Continuing from: {existing_file}")
            results_data = self._load_results_file(existing_file)
            self._completed_tasks_info = self._get_completed_tasks_info(results_data)
            self._results_filename = existing_file
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._results_filename = self._create_results_file(framework_name, model or "unknown", timestamp)
            self._completed_tasks_info = {}
        
        print(f"📁 Results file: {self._results_filename}")
        self._task_stats = {}
    
    def _create_results_file(self, framework_name, model, timestamp):
        """Create initial results file."""
        os.makedirs("outputs", exist_ok=True)
        
        framework_safe = framework_name.lower().replace(" ", "_")
        filename = f"outputs/{framework_safe}_{self.dataset_name}_{self.mode}_{timestamp}.json"
        
        tasks_to_run = self.get_tasks_to_run()
        
        initial_results = {
            'framework': framework_name,
            'dataset': self.dataset_name,
            'model': model,
            'mode': self.mode,
            'tasks_run': len(tasks_to_run),
            'tasks_list': tasks_to_run,
            'timestamp': timestamp,
            'status': 'running',
            'overall_accuracy': 0.0,
            'total_questions': 0,
            'correct_answers': 0,
            'detailed_results': []
        }
        
        with open(filename, 'w') as f:
            json.dump(initial_results, f, indent=2)
        
        return filename
    
    def _load_results_file(self, filename):
        """Load existing results file."""
        with open(filename, 'r') as f:
            return json.load(f)
    
    def _get_completed_tasks_info(self, results_data):
        """Get completed tasks info from results data."""
        completed_tasks_info = {}
        for entry in results_data.get('detailed_results', []):
            task_name = entry['task']
            completed_tasks_info[task_name] = completed_tasks_info.get(task_name, 0) + 1
        return completed_tasks_info
    
    def _add_result_to_file(self, metadata, raw_agent_output, extracted_answer, is_correct, result_metadata=None):
        """Add result entry to results file."""
        results_data = self._load_results_file(self._results_filename)
        
        input_field = self.dataset_config['input_field']
        question_text = metadata['question_data'][input_field] if isinstance(metadata['question_data'], dict) else str(metadata['question_data'])
        
        result_entry = {
            'task': metadata['task_name'],
            'question_index': metadata['question_index'],
            'question': question_text,
            'raw_agent_output': raw_agent_output,
            'extracted_answer': extracted_answer,
            'target_answer': metadata['target_answer'],
            'target_classes': metadata['target_classes'],
            'datatype': metadata['datatype'],
            'is_correct': is_correct
        }
        
        # Add metadata if provided
        if result_metadata:
            result_entry['meta'] = result_metadata
        
        results_data['detailed_results'].append(result_entry)
        results_data['total_questions'] = len(results_data['detailed_results'])
        results_data['correct_answers'] = sum(1 for r in results_data['detailed_results'] if r['is_correct'])
        results_data['overall_accuracy'] = (results_data['correct_answers'] / results_data['total_questions'] * 100) if results_data['total_questions'] > 0 else 0.0
        
        with open(self._results_filename, 'w') as f:
            json.dump(results_data, f, indent=2)


def extract_answer(agent_output, target_classes, datatype, original_question=None, extraction_config=None):
    """Extract final answer using OpenAI API with strict target class matching and retry logic."""
    
    # Default values with config overrides
    if not extraction_config:
        extraction_config = {}
    model = extraction_config.get('model', 'gpt-4.1-mini')
    max_tokens = extraction_config.get('max_tokens', 50)
    temperature = extraction_config.get('temperature', 0)
    timeout = extraction_config.get('timeout', 30)
    
    # Retry configuration with exponential backoff
    max_retries = 5
    base_retry_delay = 5  # seconds
    
    # Create few-shot examples for the prompt
    examples = """Examples of extraction with context mapping:

Original question: "Is the following statement logically valid: All cats are animals, Fluffy is a cat, therefore Fluffy is an animal?"
Agent response: "Let me think step by step. This is a valid syllogism. The answer is True."
Target classes: ["True", "False"]
Extracted: True

Original question: "Which option best describes the weather: (A) Sunny (B) Rainy (C) Cloudy (D) Snowy?"
Agent response: "After analyzing the conditions, it appears to be raining outside."
Target classes: ["(A)", "(B)", "(C)", "(D)"]
Extracted: (B)

Original question: "How many objects are red in the image?"
Agent response: "I can see three red objects in total."
Target classes: ["1", "2", "3", "4", "5"]
Extracted: 3

Original question: "What is the capital of France?"
Agent response: "The capital is Paris."
Target classes: ["London", "Berlin", "Madrid", "Rome"]
Extracted: null

Original question: "Is this statement correct: 2+2=4?"
Agent response: "Yes, that's correct."
Target classes: ["True", "False"]
Extracted: True

Original question: "Choose the best answer: (A) Red (B) Blue (C) Green"
Agent response: "The grass color would be green."
Target classes: ["(A)", "(B)", "(C)"]
Extracted: (C)"""

    # Build the prompt with optional question context
    question_context = ""
    if original_question:
        question_context = f"""
Original question (for context only): {original_question}
"""

    prompt = f"""{examples}

IMPORTANT INSTRUCTIONS:
1. Use the original question ONLY as context to understand what the agent is responding to
2. Find the agent's intended answer by understanding both the question context and the agent's response
3. Map the agent's answer to the EXACT target class format (including brackets, capitalization)
4. If the agent gives a value/description that corresponds to a target class, map it correctly
5. If you cannot confidently map to exactly one target class, return "null"
6. DO NOT alter or interpret the agent's reasoning - only extract their final choice
7. Some agent responses can be very long and big, processes them carefully to find the answer the agent is suggesting.

Original question: 
```
{question_context}
```

Agent response: 
```
{agent_output}
```

Target classes: {target_classes}
Expected datatype: {datatype}

Extracted answer:"""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("    Warning: OPENAI_API_KEY not set, extraction will fail")
        return None

    # Retry logic for extraction
    messages = [{"role": "user", "content": prompt}]
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=timeout
            )
            
            # Handle successful response
            if response.status_code == 200:
                response_data = response.json()
                extracted = response_data["choices"][0]["message"]["content"].strip()

                # Log token usage
                if "usage" in response_data:
                    usage = response_data["usage"]
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    print(f"    Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")

                if extracted.lower() == "null":
                    return None
                if extracted in target_classes:
                    return extracted
                
                # Format error - add to conversation for retry
                if attempt < max_retries - 1:
                    messages.append({"role": "assistant", "content": extracted})
                    messages.append({"role": "user", "content": f"'{extracted}' not in target classes -> {target_classes}. Probably some formatting issue, please provide the exact formatting of target based mapping or null if not available."})
                    error_msg = f"'{extracted}' not in target classes, continuing conversation"
                else:
                    error_msg = f"'{extracted}' not in target classes -> {target_classes}"
            else:
                error_msg = f"OpenAI API error {response.status_code}"
                
        except Exception as e:
            error_msg = f"Extraction error: {e}"
        
        # Retry logic with exponential backoff
        if attempt < max_retries - 1:
            # Calculate delay: 5s, 10s, 20s, 40s for attempts 1-4
            current_delay = base_retry_delay * (2 ** attempt)
            print(f"    Extraction attempt {attempt + 1} failed: {error_msg}, retrying in {current_delay}s...")
            time.sleep(current_delay)
        else:
            print(f"    Extraction failed after {max_retries} attempts: {error_msg}")
            return None
    
    return None


