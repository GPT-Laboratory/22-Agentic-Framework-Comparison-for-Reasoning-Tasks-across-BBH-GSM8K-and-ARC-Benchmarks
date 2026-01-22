"""
BBH (Big Bench Hard) dataset loader.
"""

import time
from datasets import load_dataset
from .base_loader import BaseDatasetLoader


class BBHLoader(BaseDatasetLoader):
    """Loader for BBH dataset."""
    
    def load_dataset_data(self, task_name=None):
        """Load BBH dataset data for a specific task."""
        repo = self.dataset_config['repo']
        
        for attempt in range(10):
            try:
                print(f"    Loading {repo}:{task_name} (attempt {attempt + 1})...")
                dataset = load_dataset(repo, task_name)
                split_name = self.dataset_config['splits'].get('train', 'train')
                return dataset[split_name]
            except Exception as e:
                if attempt < 9:
                    time.sleep(5 * (2 ** attempt))
                else:
                    raise e
    
    def format_prompt(self, question_data, few_shot_examples, enable_cot):
        """Format BBH-style prompt with few-shot examples."""
        prompt_parts = []
        input_field = self.dataset_config['input_field']
        target_field = self.dataset_config['target_field']
        
        for example in few_shot_examples:
            if enable_cot:
                prompt_parts.append(f"Q: {example[input_field]}\\nA: Let me think step by step. {example[target_field]}")
            else:
                prompt_parts.append(f"Q: {example[input_field]}\\nA: {example[target_field]}")
        
        question_text = f"Q: {question_data[input_field]}\\nA:"
        if enable_cot:
            question_text += " Let me think step by step."
        
        prompt_parts.append(question_text)
        return "\\n\\n".join(prompt_parts)
    
    def extract_target_answer(self, raw_target):
        """BBH targets are already clean."""
        return raw_target
    
    def extract_agent_answer(self, agent_output, target_classes, datatype, original_question=None):
        """Extract BBH answer using centralized extraction function."""
        from utils import extract_answer
        return extract_answer(agent_output, target_classes, datatype, original_question, self.dataset_config['extraction'])
    
    def get_target_classes_and_datatype(self, dataset_data):
        """Extract target classes and determine datatype from BBH dataset."""
        target_field = self.dataset_config['target_field']
        all_targets = [str(item[target_field]).strip() for item in dataset_data]
        target_classes = list(set(all_targets))
        
        sample_target = target_classes[0] if target_classes else ""
        if sample_target.lower() in ['true', 'false']:
            datatype = "boolean"
        elif sample_target.startswith('(') and sample_target.endswith(')'):
            datatype = "multiple_choice"
        elif sample_target.isdigit():
            datatype = "number"
        else:
            datatype = "string"
        
        return target_classes, datatype