"""
GSM8K (Grade School Math 8K) dataset loader.
"""

import re
import time
import requests
import os
from datasets import load_dataset
from .base_loader import BaseDatasetLoader


class GSM8KLoader(BaseDatasetLoader):
    """Loader for GSM8K dataset."""
    
    def load_dataset_data(self, task_name=None):
        """Load GSM8K dataset data."""
        repo = self.dataset_config['repo']
        config_name = self.dataset_config['config']
        
        for attempt in range(10):
            try:
                print(f"    Loading {repo} (attempt {attempt + 1})...")
                print(f"    Using config: {config_name}")
                dataset = load_dataset(repo, config_name)
                split_name = self.dataset_config['splits'].get('train', 'train')
                return dataset[split_name]
            except Exception as e:
                if attempt < 9:
                    time.sleep(5 * (2 ** attempt))
                else:
                    raise e
    
    def format_prompt(self, question_data, few_shot_examples, enable_cot):
        """Format GSM8K-style prompt with few-shot examples."""
        prompt_parts = []
        input_field = self.dataset_config['input_field']
        target_field = self.dataset_config['target_field']
        
        for example in few_shot_examples:
            if enable_cot:
                prompt_parts.append(f"Question: {example[input_field]}\\nAnswer: Let me think step by step. {example[target_field]}")
            else:
                prompt_parts.append(f"Question: {example[input_field]}\\nAnswer: {example[target_field]}")
        
        question_text = f"Question: {question_data[input_field]}\\nAnswer:"
        if enable_cot:
            question_text += " Let me think step by step."
        
        prompt_parts.append(question_text)
        return "\\n\\n".join(prompt_parts)
    
    def extract_target_answer(self, raw_target):
        """Extract numerical answer from GSM8K target (format: explanation\\n#### 42)."""
        if "####" in raw_target:
            return raw_target.split("####")[-1].strip()
        return raw_target
    
    def extract_agent_answer(self, agent_output, target_classes, datatype, original_question=None):
        """Extract numerical answer from GSM8K using centralized extraction function."""
        from utils import extract_answer
        return extract_answer(agent_output, target_classes, datatype, original_question, self.dataset_config['extraction'])
    
    def generate_metadata(self, agent_output, target_answer, original_question):
        """Generate metadata for GSM8K including reasoning alignment score."""
        reasoning_score = self.score_gsm8k_reasoning(agent_output, target_answer, original_question)
        return {
            "reasoning_alignment": str(reasoning_score)
        }
    
    def score_gsm8k_reasoning(self, agent_output, target_answer, original_question):
        """Score GSM8K reasoning quality from 0.0 to 1.0 comparing agent answer with dataset answer."""
        extraction_config = self.dataset_config['extraction']
        
        # Default values with config overrides
        model = extraction_config.get('model', 'gpt-4.1-mini')
        max_tokens = extraction_config.get('max_tokens', 200)
        temperature = extraction_config.get('temperature', 0)
        timeout = extraction_config.get('timeout', 30)
        
        prompt = f"""You are evaluating the quality of mathematical reasoning for a Grade School Math (GSM8K) problem.

SCORING CRITERIA:
- 1.0: Perfect answer with correct final result AND correct reasoning steps
- 0.8-0.9: Correct final answer with mostly correct reasoning (minor computational errors in steps)
- 0.6-0.7: Correct final answer but with some flawed reasoning or missing steps  
- 0.5: Correct final answer but reasoning is mostly incorrect or incomplete
- 0.3-0.4: Incorrect final answer but shows understanding of the problem and some correct reasoning
- 0.1-0.2: Incorrect final answer with poor reasoning but some relevant mathematical concepts
- 0.0: Completely incorrect or irrelevant response

QUESTION:
{original_question}

CORRECT DATASET ANSWER:
{target_answer}

AGENT'S ANSWER:
{agent_output}

Provide ONLY a single decimal score between 0.0 and 1.0 (e.g., 0.8)."""

        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("    Warning: OPENAI_API_KEY not set, scoring will fail")
                return 0.0
                
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                score_text = result["choices"][0]["message"]["content"].strip()
                
                # Extract numeric score
                try:
                    score = float(score_text)
                    return max(0.0, min(1.0, score))  # Clamp between 0.0 and 1.0
                except ValueError:
                    print(f"    Could not parse score: {score_text}")
                    return 0.0
            else:
                print(f"    OpenAI API error: {response.status_code}")
                return 0.0
                
        except Exception as e:
            print(f"    Scoring error: {e}")
            return 0.0
    
    def get_target_classes_and_datatype(self, dataset_data):
        """Extract numerical targets from GSM8K dataset."""
        target_field = self.dataset_config['target_field']
        all_targets = []
        
        for item in list(dataset_data)[:100]:  # Sample first 100 for target classes
            answer = item[target_field]
            if "####" in answer:
                number = answer.split("####")[-1].strip()
                all_targets.append(number)
        
        return list(set(all_targets)), "number"