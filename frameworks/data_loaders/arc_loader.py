"""
ARC (AI2 Reasoning Challenge) dataset loader.
"""

import time
from datasets import load_dataset
from .base_loader import BaseDatasetLoader


class ARCLoader(BaseDatasetLoader):
    """Loader for ARC dataset."""
    
    def load_dataset_data(self, task_name=None):
        """Load ARC dataset data for a specific task."""
        repo = self.dataset_config['repo']
        
        for attempt in range(10):
            try:
                print(f"    Loading {repo} (attempt {attempt + 1})...")
                # ARC has subtasks (ARC-Easy, ARC-Challenge)
                subtask = task_name if task_name else 'ARC-Easy'
                dataset = load_dataset(repo, subtask)
                split_name = self.dataset_config['splits'].get('train', 'train')
                return dataset[split_name]
            except Exception as e:
                if attempt < 9:
                    time.sleep(5 * (2 ** attempt))
                else:
                    raise e
    
    def format_prompt(self, question_data, few_shot_examples, enable_cot):
        """Format ARC-style prompt with few-shot examples."""
        prompt_parts = []
        
        for example in few_shot_examples:
            question = example['question']
            
            # Handle different choice formats
            if isinstance(example['choices'], dict):
                labels = example['choices']['label']
                texts = example['choices']['text']
                choices = "\\n".join([f"({label}) {text}" for label, text in zip(labels, texts)])
            else:
                choices = "\\n".join([f"({choice['label']}) {choice['text']}" for choice in example['choices']])
            
            answer = example['answerKey']
            
            if enable_cot:
                prompt_parts.append(f"Question: {question}\\n{choices}\\nAnswer: Let me think step by step. ({answer})")
            else:
                prompt_parts.append(f"Question: {question}\\n{choices}\\nAnswer: ({answer})")
        
        question = question_data['question']
        
        # Handle different choice formats for main question
        if isinstance(question_data['choices'], dict):
            labels = question_data['choices']['label']
            texts = question_data['choices']['text']
            choices = "\\n".join([f"({label}) {text}" for label, text in zip(labels, texts)])
        else:
            choices = "\\n".join([f"({choice['label']}) {choice['text']}" for choice in question_data['choices']])
        
        question_text = f"Question: {question}\\n{choices}\\nAnswer:"
        if enable_cot:
            question_text += " Let me think step by step."
        
        prompt_parts.append(question_text)
        return "\\n\\n".join(prompt_parts)
    
    def extract_target_answer(self, raw_target):
        """ARC targets are already clean (A, B, C, D)."""
        return raw_target
    
    def extract_agent_answer(self, agent_output, target_classes, datatype, original_question=None):
        """Extract ARC answer using centralized extraction function."""
        from utils import extract_answer
        return extract_answer(agent_output, target_classes, datatype, original_question, self.dataset_config['extraction'])
    
    def get_target_classes_and_datatype(self, dataset_data):
        """ARC targets are A, B, C, D multiple choice."""
        return ["A", "B", "C", "D"], "multiple_choice"