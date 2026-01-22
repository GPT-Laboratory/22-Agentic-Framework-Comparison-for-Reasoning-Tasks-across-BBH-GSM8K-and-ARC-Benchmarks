#!/usr/bin/env python3
"""
Multi-dataset configuration-based runner for benchmarking frameworks.
Supports any datasets defined in datasets.yml configuration.
"""

import os
import sys
import yaml
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import threading
import time

# Global dataset configuration - loaded once at module level
DATASET_CONFIGS = None
DEFAULT_DATASET = None

def initialize_dataset_configs():
    """Initialize global dataset configuration and default dataset."""
    global DATASET_CONFIGS, DEFAULT_DATASET
    if DATASET_CONFIGS is None:
        DATASET_CONFIGS = load_datasets_config()
        available_datasets = list(DATASET_CONFIGS['datasets'].keys())
        DEFAULT_DATASET = available_datasets[0] if available_datasets else None


def log_with_timestamp(log_file, message, level="INFO"):
    """Write a message to log file with timestamp and log level."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Include milliseconds
    formatted_message = f"[{timestamp}] [{level}] {message}\n"
    log_file.write(formatted_message)
    log_file.flush()


def stream_process_output(process, log_file):
    """Stream process output in real-time with timestamps."""
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            # Strip newline and add timestamped log entry
            clean_output = output.rstrip('\n\r')
            if clean_output:  # Don't log empty lines
                log_with_timestamp(log_file, clean_output, "OUTPUT")
    
    # Log process completion
    return_code = process.poll()
    log_with_timestamp(log_file, f"Process completed with exit code: {return_code}", "SYSTEM")


def create_log_directory():
    """Create timestamped log directory for this run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs") / f"run_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def load_env_file():
    """Load environment variables from .env file if it exists."""
    # Check for .env in parent directory (root of project)
    env_file = os.path.join("..", ".env")
    if not os.path.exists(env_file):
        # Check for .env in current directory
        env_file = ".env"
        if not os.path.exists(env_file):
            # Check for .env in root if we're in frameworks directory
            env_file = os.path.join("..", "..", ".env")
            if not os.path.exists(env_file):
                return
    
    print(f"🔑 Loading environment variables from {env_file}")
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key] = value
        print(f"✅ Environment variables loaded successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not load .env file: {e}")


def load_config(config_file="config.yml"):
    """Load and parse the YAML configuration file."""
    # Handle being run from different directories
    if not os.path.exists(config_file):
        # Check if we're in the root directory
        frameworks_config = os.path.join("frameworks", config_file)
        if os.path.exists(frameworks_config):
            config_file = frameworks_config
        else:
            print(f"❌ {config_file} not found")
            print("Please ensure config.yml exists in frameworks/ directory")
            sys.exit(1)
    
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_datasets_config():
    """Load datasets configuration from datasets.yml."""
    datasets_file = "datasets.yml"
    if not os.path.exists(datasets_file):
        frameworks_datasets = os.path.join("frameworks", datasets_file)
        if os.path.exists(frameworks_datasets):
            datasets_file = frameworks_datasets
        else:
            print(f"❌ datasets.yml not found")
            sys.exit(1)
    
    with open(datasets_file, 'r') as f:
        return yaml.safe_load(f)


def get_framework_setting(config, framework, setting):
    """Get a setting for a framework, falling back to commons if not specified."""
    # Check framework-specific setting first
    if 'frameworks' in config and framework in config['frameworks']:
        framework_config = config['frameworks'][framework]
        if setting in framework_config and framework_config[setting] is not None:
            return framework_config[setting]
    
    # Fall back to commons
    if 'commons' in config and setting in config['commons']:
        return config['commons'][setting]
    
    return None


def build_command_args(config, framework, dataset_name, mode):
    """Build command line arguments based on configuration."""
    args = []
    
    # Add dataset argument
    args.append(f'--dataset={dataset_name}')
    
    # Check mode setting
    if mode == 'full':
        args.append('--full')
    
    # Check continue_mode setting
    continue_mode = get_framework_setting(config, framework, 'continue_mode')
    if continue_mode is True:
        args.append('--continue')
    
    return args


def run_framework(framework, args, config, log_dir, config_filename="config.yml", dataset_name=None):
    """Run a specific framework with given arguments."""
    # Use default dataset if none provided
    if dataset_name is None:
        initialize_dataset_configs()
        dataset_name = DEFAULT_DATASET or "unknown"
    # Handle different working directories
    if os.path.exists("frameworks"):
        # We're in root directory
        framework_dir = Path("frameworks") / framework
    else:
        # We're in frameworks directory
        framework_dir = Path(framework)
    
    if not framework_dir.exists():
        print(f"⚠️  Framework directory {framework} not found, skipping...")
        return False
    
    main_py = framework_dir / "main.py"
    if not main_py.exists():
        print(f"⚠️  {main_py} not found, skipping...")
        return False
    
    # Get framework settings for display
    mode = 'full' if '--full' in args else 'sample'
    continue_mode = get_framework_setting(config, framework, 'continue_mode')
    model = get_framework_setting(config, framework, 'model')
    
    print(f"🔄 Running {framework}...")
    print(f"  📋 Settings for {framework}:")
    print(f"    - Dataset: {dataset_name}")
    print(f"    - Mode: {mode}")
    print(f"    - Continue mode: {continue_mode}")
    print(f"    - Model: {model}")
    print(f"    - Command args: {' '.join(args)}")
    
    # Prepare environment
    env = os.environ.copy()
    if model:
        env['BENCHMARK_MODEL'] = str(model)  # New variable
    
    # Build command
    cmd = ['uv', 'run', 'main.py'] + args
    print(f"  ▶️  Executing: {' '.join(cmd)}")
    
    # Create log file name
    config_name = Path(config_filename).stem
    log_filename = f"{framework}_{dataset_name}_{mode}_{config_name}.log"
    log_file = log_dir / log_filename
    
    try:
        # Open log file for real-time writing
        with open(log_file, 'w', encoding='utf-8', buffering=1) as log_f:
            # Force truly unbuffered output using stdbuf and environment variables
            env_unbuffered = env.copy()
            env_unbuffered['PYTHONUNBUFFERED'] = '1'
            
            # Use stdbuf to disable all buffering for the subprocess
            unbuffered_cmd = ['stdbuf', '-o0', '-e0'] + cmd
            
            # Log session header with timestamps
            log_with_timestamp(log_f, "=" * 60, "SYSTEM")
            log_with_timestamp(log_f, f"Framework Execution Session Started", "SYSTEM")
            log_with_timestamp(log_f, f"Framework: {framework}", "INFO")
            log_with_timestamp(log_f, f"Dataset: {dataset_name}", "INFO") 
            log_with_timestamp(log_f, f"Config: {config_filename}", "INFO")
            log_with_timestamp(log_f, f"Original Command: {' '.join(cmd)}", "INFO")
            log_with_timestamp(log_f, f"Unbuffered Command: {' '.join(unbuffered_cmd)}", "INFO")
            log_with_timestamp(log_f, f"Working Directory: {framework_dir}", "INFO")
            log_with_timestamp(log_f, "=" * 60, "SYSTEM")
            
            # Start process with unbuffered output for true real-time streaming
            process = subprocess.Popen(
                unbuffered_cmd,
                cwd=framework_dir,
                env=env_unbuffered,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                text=True,
                bufsize=0,  # Unbuffered for real-time
                universal_newlines=True
            )
            
            log_with_timestamp(log_f, f"Process started with PID: {process.pid}", "SYSTEM")
            
            # Stream output in real-time using a separate thread
            def stream_output():
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        # Strip newline and add timestamped log entry
                        clean_output = output.rstrip('\n\r')
                        if clean_output:  # Don't log empty lines
                            log_with_timestamp(log_f, clean_output, "OUTPUT")
            
            # Start streaming in background thread for true real-time
            stream_thread = threading.Thread(target=stream_output, daemon=True)
            stream_thread.start()
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Wait for streaming thread to finish
            stream_thread.join(timeout=5)
            
            log_with_timestamp(log_f, f"Process completed with exit code: {return_code}", "SYSTEM")
            log_with_timestamp(log_f, "Framework Execution Session Ended", "SYSTEM")
            
            if return_code != 0:
                raise subprocess.CalledProcessError(return_code, cmd)
        
        print(f"  ✅ {framework} completed successfully")
        print(f"  📝 Log saved to: {log_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ {framework} failed with exit code {e.returncode}")
        
        # Add error summary to log with timestamp
        with open(log_file, 'a', encoding='utf-8', buffering=1) as log_f:
            log_with_timestamp(log_f, f"PROCESS FAILED with exit code: {e.returncode}", "ERROR")
            log_with_timestamp(log_f, "Framework Execution Session Ended with Error", "SYSTEM")
        
        print(f"  📝 Error log saved to: {log_file}")
        return False
    except Exception as e:
        print(f"  ❌ {framework} failed with error: {e}")
        
        # Write exception to log file with timestamp
        with open(log_file, 'a', encoding='utf-8', buffering=1) as log_f:
            log_with_timestamp(log_f, f"EXCEPTION: {type(e).__name__}: {str(e)}", "ERROR")
            log_with_timestamp(log_f, "Framework Execution Session Ended with Exception", "SYSTEM")
        
        print(f"  📝 Error log saved to: {log_file}")
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Multi-dataset configuration-based runner for benchmarking frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                        # Use default config.yml with datasets from config
  %(prog)s --config custom.yml                    # Use custom configuration file
  %(prog)s --dataset custom_dataset              # Run specific dataset (overrides config)
  %(prog)s --dataset custom_dataset --mode full  # Run specific dataset in full mode
  %(prog)s --list-datasets                       # List available datasets
  %(prog)s --list-frameworks                     # List available frameworks
  
The configuration file should be in YAML format and contain:
- commons: Default settings for all frameworks
- frameworks: Framework-specific overrides
- frameworks_to_run: List of frameworks to execute

Dataset configurations are defined in datasets.yml.
        """)
    
    parser.add_argument(
        "--config", "-c",
        default="config.yml",
        help="Configuration file to use (default: config.yml)"
    )
    
    parser.add_argument(
        "--dataset", "-d",
        default=None,
        help="Dataset to run (overrides config datasets_to_run). See --list-datasets for available options."
    )
    
    parser.add_argument(
        "--mode", "-m",
        choices=["sample", "full"],
        default="sample",
        help="Run mode: sample (default) or full"
    )
    
    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="List all available datasets and exit"
    )
    
    parser.add_argument(
        "--list-frameworks", "-l",
        action="store_true",
        help="List all available frameworks and exit"
    )
    
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()
    
    print("📋 Multi-Dataset Framework Configuration Runner")
    print("=" * 50)
    
    # Load environment variables from .env file
    load_env_file()
    
    # Initialize global datasets configuration
    initialize_dataset_configs()
    global DATASET_CONFIGS, DEFAULT_DATASET
    
    # Handle --list-datasets flag
    if args.list_datasets:
        available_datasets = list(DATASET_CONFIGS['datasets'].keys())
        print(f"\n📊 Available datasets ({len(available_datasets)} total):")
        for dataset in available_datasets:
            dataset_info = DATASET_CONFIGS['datasets'][dataset]
            print(f"  • {dataset}: {dataset_info.get('name', 'Unknown')}")
        sys.exit(0)
    
    # Load configuration
    config_filename = args.config
    print(f"📄 Using configuration file: {config_filename}")
    config = load_config(config_filename)
    
    # Determine datasets to run - priority: CLI arg > config > first available dataset
    datasets_to_run = []
    if args.dataset:  # CLI argument was provided
        datasets_to_run = [args.dataset]
        print(f"📊 Using CLI dataset: {args.dataset} (mode: {args.mode})")
    else:
        # Check for datasets_to_run in config
        config_datasets = config.get('datasets_to_run', [])
        if config_datasets:
            datasets_to_run = config_datasets
            print(f"📊 Using config datasets: {', '.join(datasets_to_run)} (mode: {args.mode})")
        else:
            # Use default dataset as fallback
            if DEFAULT_DATASET:
                datasets_to_run = [DEFAULT_DATASET]
                print(f"📊 Using default dataset: {DEFAULT_DATASET} (mode: {args.mode})")
            else:
                print("❌ No datasets available in datasets.yml")
                sys.exit(1)
    
    # Validate all datasets
    available_datasets = list(DATASET_CONFIGS['datasets'].keys())
    for dataset in datasets_to_run:
        if dataset not in available_datasets:
            print(f"❌ Dataset '{dataset}' not found. Available datasets: {', '.join(available_datasets)}")
            sys.exit(1)
    
    # Create log directory for this run
    log_dir = create_log_directory()
    print(f"📁 Logs will be saved to: {log_dir}")
    print()
    
    # Display commons settings
    commons = config.get('commons', {})
    frameworks_to_run_config = config.get('frameworks_to_run', [])
    
    print("📊 Commons settings:")
    print(f"  - Default mode: {commons.get('sample_mode', 'not set')}")
    print(f"  - Continue mode: {commons.get('continue_mode', 'not set')}")
    print(f"  - Default model: {commons.get('model', 'not set')}")
    frameworks_display = frameworks_to_run_config if frameworks_to_run_config else 'all frameworks'
    if frameworks_to_run_config and "all" in frameworks_to_run_config:
        frameworks_display = 'all frameworks'
    print(f"  - Framework filter: {frameworks_display}")
    
    # Get frameworks to run - either from config or discover all
    frameworks_to_run = config.get('frameworks_to_run', [])
    
    # Get all available frameworks from filesystem
    # Handle being run from different directories
    if os.path.exists("frameworks"):
        frameworks_dir = "frameworks"
    else:
        frameworks_dir = "."
    
    # Find all framework directories (starting with fm_)
    all_frameworks = []
    for item in os.listdir(frameworks_dir):
        item_path = os.path.join(frameworks_dir, item)
        if os.path.isdir(item_path) and item.startswith("fm_"):
            main_py = os.path.join(item_path, "main.py")
            if os.path.exists(main_py):
                all_frameworks.append(item)
    
    all_frameworks.sort()  # Consistent ordering
    
    # Handle --list-frameworks flag
    if args.list_frameworks:
        print(f"\n📋 Available frameworks ({len(all_frameworks)} total):")
        for framework in all_frameworks:
            print(f"  • {framework}")
        sys.exit(0)
    
    # Filter frameworks based on configuration
    if frameworks_to_run:
        # Check if "all" is specified
        if "all" in frameworks_to_run:
            # Run all available frameworks
            frameworks = all_frameworks
        else:
            # Validate specified frameworks exist
            frameworks = []
            for fw in frameworks_to_run:
                if fw in all_frameworks:
                    frameworks.append(fw)
                else:
                    print(f"⚠️  Framework '{fw}' specified in config but not found, skipping...")
            
            if not frameworks:
                print("❌ No valid frameworks specified in frameworks_to_run")
                sys.exit(1)
    else:
        # Run all available frameworks
        frameworks = all_frameworks
    
    print(f"\n🎯 Found {len(frameworks)} frameworks to run: {', '.join(frameworks)}")
    print(f"📊 Found {len(datasets_to_run)} datasets to run: {', '.join(datasets_to_run)}")
    
    # Show dataset details
    for dataset in datasets_to_run:
        dataset_info = DATASET_CONFIGS['datasets'][dataset] if DATASET_CONFIGS else {}
        print(f"  • {dataset}: {dataset_info.get('name', dataset)} ({args.mode} mode)")
    
    print(f"\n🎯 Total executions: {len(frameworks)} frameworks × {len(datasets_to_run)} datasets = {len(frameworks) * len(datasets_to_run)} runs")
    print("\n🚀 Starting framework execution...")
    print("=" * 50)
    
    # Run each framework for each dataset
    successful = 0
    failed = 0
    total_runs = len(frameworks) * len(datasets_to_run)
    current_run = 0
    
    for dataset in datasets_to_run:
        dataset_info = DATASET_CONFIGS['datasets'][dataset] if DATASET_CONFIGS else {}
        print(f"\n🔷 DATASET: {dataset_info.get('name', dataset)} ({dataset})")
        print("=" * 50)
        
        for framework in frameworks:
            current_run += 1
            print(f"\n[{current_run}/{total_runs}] Running {framework} on {dataset}...")
            cmd_args = build_command_args(config, framework, dataset, args.mode)
            
            if run_framework(framework, cmd_args, config, log_dir, config_filename, dataset):
                successful += 1
            else:
                failed += 1
            
            print("-" * 30)
    
    # Summary
    print(f"\n🎉 Execution completed!")
    print(f"✅ Successful: {successful}/{total_runs}")
    print(f"❌ Failed: {failed}/{total_runs}")
    print(f"📝 All logs saved to: {log_dir}")
    print("📁 Check individual framework outputs/ directories for results")


if __name__ == "__main__":
    main()