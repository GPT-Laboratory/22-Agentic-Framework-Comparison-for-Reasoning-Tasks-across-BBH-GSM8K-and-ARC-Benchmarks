#!/bin/bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

main() {
    # Parse command line arguments
    local dataset=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --ds)
                dataset="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--ds dataset_name]"
                echo "  --ds: specify dataset (bbh, arc, gsm8k)"
                exit 1
                ;;
        esac
    done

    echo "🚀 BBH Framework Evaluation"
    echo

    # Check .run_config
    if [ ! -f ".run_config" ]; then
        print_error ".run_config not found. Run 'scripts/setup.sh' first."
        exit 1
    fi

    # Parse setup status
    local setup_complete=$(python3 -c "import json; print(json.load(open('.run_config')).get('setup_complete', False))" 2>/dev/null || echo "false")

    if [ "$setup_complete" != "True" ]; then
        print_error "Setup not complete. Run 'scripts/setup.sh' first."
        exit 1
    fi

    print_success "Setup verified"

    # Load .env
    if [ -f ".env" ]; then
        source .env
        print_success ".env loaded"
    fi

    echo
    read -p "Run sample evaluation? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi

    # Run evaluation
    print_info "Running evaluation..."
    if [ -n "$dataset" ]; then
        print_info "Running with specific dataset: $dataset"
        if uv run frameworks/run_config.py --dataset "$dataset"; then
            print_success "Evaluation complete"
        else
            print_error "Evaluation failed"
            exit 1
        fi
    else
        if uv run frameworks/run_config.py; then
            print_success "Evaluation complete"
        else
            print_error "Evaluation failed"
            exit 1
        fi
    fi
    
    echo
    read -p "Run analysis? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    
    # # Run analysis
    uv run jupyter nbconvert --to notebook --execute --inplace analysis2.ipynb
    
    echo
    print_success "All done! Check results in frameworks/*/outputs/ and analysis.ipynb"
}

main "$@"
