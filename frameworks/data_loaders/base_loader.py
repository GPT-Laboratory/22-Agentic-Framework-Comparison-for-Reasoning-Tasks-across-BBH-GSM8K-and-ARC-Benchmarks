"""
Base dataset loader interface.
"""

from abc import ABC, abstractmethod


class BaseDatasetLoader(ABC):
    """Base interface for dataset loaders."""
    
    def __init__(self, dataset_config):
        self.dataset_config = dataset_config
    
    @abstractmethod
    def load_dataset_data(self, task_name=None):
        """Load dataset data for a specific task."""
        pass
    
    @abstractmethod
    def format_prompt(self, question_data, few_shot_examples, enable_cot):
        """Format prompt for this dataset type."""
        pass
    
    @abstractmethod
    def extract_target_answer(self, raw_target):
        """Extract clean target answer from raw dataset target."""
        pass
    
    @abstractmethod
    def extract_agent_answer(self, agent_output, target_classes, datatype, original_question=None):
        """Extract agent's answer from raw output."""
        pass
    
    @abstractmethod
    def get_target_classes_and_datatype(self, dataset_data):
        """Extract target classes and determine datatype from dataset."""
        pass

    def get_system_prompt_override(self):
        """
        Get dataset-specific system prompt override.
        Returns None by default - datasets can override this to provide custom prompts.
        """
        return None