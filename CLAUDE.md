# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a dataset-agnostic benchmarking repository that evaluates multiple agentic AI frameworks across various reasoning datasets. The system supports multiple datasets through a modular loader architecture and configuration-driven execution.

## Architecture

**Core Structure:**
- `frameworks/` - Contains framework implementations (fm_autogen, fm_swarm, fm_crewai, etc.)
- `frameworks/utils.py` - Unified multi-dataset evaluation utilities 
- `frameworks/data_loaders/` - Modular dataset-specific loaders (BBH, GSM8K, ARC, etc.)
- `frameworks/datasets.yml` - Dataset configurations and specifications
- `frameworks/config.yml` - Framework execution configuration
- `frameworks/run_config.py` - Multi-dataset configuration-based runner
- `scripts/setup.sh` - Automated setup script for all frameworks
- `run.sh` - Main execution script

**Framework Implementation Pattern:**
Each framework follows a consistent structure:
- `main.py` - Framework-specific implementation using shared utilities
- `pyproject.toml` - Dependencies managed by uv package manager  
- `outputs/` - JSON results files with detailed evaluation data

**Dataset Loader System:**
Modular loaders in `data_loaders/` handle dataset-specific logic:
- `base_loader.py` - Abstract base class defining loader interface
- `bbh_loader.py` - Big Bench Hard dataset loader
- `gsm8k_loader.py` - Grade School Math 8K loader
- `arc_loader.py` - AI2 Reasoning Challenge loader
- Each loader handles prompting, formatting, and answer extraction

**Shared Evaluation Logic:**
All frameworks use `utils.py` DatasetManager which provides:
- Dataset-agnostic task loading through modular loaders
- Configurable few-shot prompting and chain-of-thought
- Unified answer extraction using OpenAI API
- Results standardization and saving

## Development Commands

**Initial setup:**
```bash
scripts/setup.sh                 # Setup all frameworks and dependencies
```

**Run evaluation:**
```bash
./run.sh                         # Interactive execution with setup verification
uv run frameworks/run_config.py  # Run with default config.yml settings
```

**Configuration-based execution:**
```bash
cd frameworks
uv run run_config.py --config custom.yml                    # Custom config file
uv run run_config.py --dataset bbh --mode full              # Specific dataset and mode
uv run run_config.py --list-datasets                        # List available datasets
uv run run_config.py --list-frameworks                      # List available frameworks
```

**Single framework execution:**
```bash
cd frameworks/fm_<framework_name>
uv run main.py --dataset=bbh                # Run with BBH dataset (sample mode)
uv run main.py --dataset=gsm8k --full      # Run with GSM8K dataset (full mode)
uv run main.py --continue                   # Continue interrupted evaluation
```

## Key Configuration Files

**datasets.yml** - Dataset specifications:
- Dataset repository information and splits
- Task lists and mode configurations (sample/full)
- Prompting settings (n_shots, enable_cot)
- Input/target field mappings
- Answer extraction settings

**config.yml** - Execution configuration:
- `frameworks_to_run` - List of frameworks to execute
- `datasets_to_run` - List of datasets to benchmark
- `commons` - Default settings (model, modes, prompting)
- `frameworks` - Framework-specific overrides

## Environment Requirements

- `OPENAI_API_KEY` - Required for answer extraction
- `uv` package manager for dependency management
- Python environments handled automatically per framework

**IMPORTANT: Use `uv run` for all Python execution in this project**
- All frameworks use `uv run main.py` instead of `python main.py`
- Configuration runner uses `uv run run_config.py` instead of `python run_config.py`
- Each framework has its own `pyproject.toml` with isolated dependencies
- Never use bare `python` commands - always use `uv run` for proper dependency resolution

## Multi-Dataset Support

The system supports multiple datasets through:
- **BBH (Big Bench Hard)** - 23 challenging reasoning tasks
- **GSM8K (Grade School Math)** - Mathematical word problems
- **ARC (AI2 Reasoning Challenge)** - Science exam questions

Each dataset has configurable:
- Sample mode (limited tasks/questions for testing)
- Full mode (complete evaluation)
- Custom prompting strategies
- Task-specific answer extraction

## Results Format

Evaluations generate JSON files with:
- Dataset and framework identification
- Overall accuracy and detailed per-question results
- Raw agent outputs and extracted answers
- Target classes and datatypes for each task