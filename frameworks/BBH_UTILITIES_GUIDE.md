# BBH Framework Utilities Guide

This guide explains how to use the standardized `BBHResultManager` utilities to ensure consistent result formatting across all BBH framework implementations.

## Why Use These Utilities?

**Problem**: Different frameworks were using inconsistent result formats, causing comparison evaluations to fail.

**Solution**: Standardized utilities ensure all frameworks use identical:
- File structures 
- Result entry formats
- Progress tracking
- Continue mode logic
- Error handling

## Quick Start

### Basic Usage

```python
from utils import BBHResultManager

# 1. Initialize manager
manager = BBHResultManager("MyFramework", "gpt-4.1-mini")

# 2. Create results file
filename = manager.create_results_file(sample_mode=True)

# 3. Process questions and add results
result_entry = manager.create_result_entry(
    task_name="boolean_expressions",
    question_index=0,
    question="not ( True ) and ( True ) is",
    raw_agent_output="Let me think step by step. The answer is False.",
    extracted_answer="False", 
    target_answer="False",
    target_classes=["True", "False"],
    datatype="boolean"
)

# 4. Add to results file
manager.add_result_entry(filename, result_entry)

# 5. Finalize when done
manager.finalize_results(filename)
```

### Full Example

See `example_framework_usage.py` for a complete implementation example.

## Key Classes and Methods

### BBHResultManager

Main class for managing BBH evaluation results.

#### Initialization
```python
manager = BBHResultManager(framework_name, model=None)
```
- `framework_name`: Name of your framework (e.g., "AutoGen", "CrewAI")
- `model`: Model name (optional, auto-detected from config/env if not provided)

#### Core Methods

##### File Management
```python
# Create new results file
filename = manager.create_results_file(sample_mode=True, timestamp=None, custom_suffix="")

# Load existing results
results_data = manager.load_results(filename)

# Save results
manager.save_results(filename, results_data)
```

##### Result Entries
```python
# Create standardized result entry
result_entry = manager.create_result_entry(
    task_name, question_index, question, raw_agent_output,
    extracted_answer, target_answer, target_classes, datatype
)

# Create error entry
error_entry = manager.create_error_entry(
    task_name, question_index, question, error,
    target_answer, target_classes, datatype
)

# Add entry to results file
manager.add_result_entry(filename, result_entry)
```

##### Progress Tracking
```python
# Update evaluation status
manager.update_status(filename, "processing", current_task="boolean_expressions")

# Finalize evaluation
final_results = manager.finalize_results(filename)
```

##### Continue Mode Support
```python
# Find latest results file
latest_file = manager.find_latest_results_file(sample_mode=True)

# Get completion info for continue mode
results_data, completed_tasks = manager.get_continue_info(filename)
```

## Required Result Entry Format

All result entries must include these standardized fields:

```json
{
  "task": "boolean_expressions",
  "question_index": 0,
  "question": "not ( True ) and ( True ) is",
  "raw_agent_output": "Let me think step by step. The answer is False.",
  "extracted_answer": "False",
  "target_answer": "False", 
  "target_classes": ["True", "False"],
  "datatype": "boolean",
  "is_correct": true
}
```

### Field Descriptions

- `task`: BBH task name
- `question_index`: 0-based index within task
- `question`: Original question text  
- `raw_agent_output`: Raw response from your framework's agent
- `extracted_answer`: Cleaned answer extracted by shared utilities
- `target_answer`: Correct answer from dataset
- `target_classes`: List of all valid answer options
- `datatype`: Type classification ("boolean", "multiple_choice", "string", "number")
- `is_correct`: Boolean indicating if extracted_answer matches target_answer

## Integration Patterns

### Pattern 1: Complete Refactor (Recommended)

Replace existing result management with utilities:

```python
# OLD - Manual result management
def create_results_file(sample_mode, timestamp):
    # ... 50+ lines of boilerplate code

# NEW - Use utilities  
manager = BBHResultManager("MyFramework", model)
filename = manager.create_results_file(sample_mode, timestamp)
```

### Pattern 2: Wrapper Functions (Backward Compatible)

Keep existing function signatures but delegate to utilities:

```python
def create_results_file(sample_mode, timestamp, model_name):
    """DEPRECATED: Use BBHResultManager instead."""
    manager = BBHResultManager("MyFramework", model_name)
    return manager.create_results_file(sample_mode, timestamp)
```

### Pattern 3: Gradual Migration

Migrate one function at a time while maintaining compatibility.

## Error Handling

Always use standardized error entries:

```python
try:
    # Your framework's agent call
    raw_output = agent.process(question)
    extracted_answer = extract_answer(raw_output, ...)
    
    result_entry = manager.create_result_entry(...)
    
except Exception as e:
    # Standardized error handling
    error_entry = manager.create_error_entry(
        task_name, question_index, question, str(e),
        target_answer, target_classes, datatype
    )
    result_entry = error_entry

manager.add_result_entry(filename, result_entry)
```

## Continue Mode Implementation

For robust continue mode support:

```python
if continue_mode:
    # Find latest results file
    results_file = manager.find_latest_results_file(sample_mode)
    if results_file:
        results_data, completed_tasks = manager.get_continue_info(results_file)
        
        # Check if task already completed
        for task_name in tasks_to_run:
            completed_count = completed_tasks.get(task_name, 0)
            if completed_count >= 3:  # Skip completed tasks
                print(f"Skipping {task_name} ({completed_count} questions done)")
                continue
```

## File Naming Convention

The utilities enforce consistent naming:
- Format: `{framework_safe}_bbh_{mode}_{timestamp}.json`
- Example: `autogen_bbh_first3tasks_20250826_123456.json`
- Mode: `first3tasks` (sample) or `full` (all 23 tasks)

## Migration Benefits

### Before (Manual Implementation)
- ❌ Inconsistent field names (`agent_output` vs `raw_agent_output`)
- ❌ Different result structures across frameworks
- ❌ Duplicate boilerplate code in every framework
- ❌ Format mismatches breaking comparison tools
- ❌ Manual error-prone progress tracking

### After (Using Utilities)
- ✅ Standardized format across all frameworks
- ✅ Automatic statistics calculation and updates
- ✅ Built-in error handling and recovery
- ✅ Consistent continue mode logic
- ✅ Reduced code duplication by 80%+

## Testing

Run the test suite to verify utilities work correctly:

```bash
cd frameworks
python test_utils.py
```

## Support

See `example_framework_usage.py` for complete implementation examples.

For questions or issues, refer to the existing implementations:
- `fm_agentzero/main.py` - Complete refactor using utilities
- `fm_autogen/main.py` - Original manual implementation
- `fm_crewai/main.py` - Original manual implementation