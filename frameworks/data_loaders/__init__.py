"""
Dataset-specific loaders and processors.
Each dataset has its own module with specialized loading and processing logic.
"""

from .bbh_loader import BBHLoader
from .gsm8k_loader import GSM8KLoader
from .arc_loader import ARCLoader

# Registry of dataset loaders
DATASET_LOADERS = {
    'bbh': BBHLoader,
    'gsm8k': GSM8KLoader, 
    'arc': ARCLoader
}