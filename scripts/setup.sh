#!/bin/bash

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Logging function with timestamp
log_msg() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $message" >> "$setup_log_file"
}

main() {
    clear
    echo "🔧 BBH Framework Setup (Minimal)"
    echo

    # Create logs directory and setup log file
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local setup_log_file=""

    # Find project root
    local project_root="."
    if [ ! -f "pyproject.toml" ]; then
        if [ -f "../pyproject.toml" ]; then
            project_root=".."
        else
            print_error "Cannot find project root"
            exit 1
        fi
    fi

    # Convert to absolute path
    project_root="$(cd "$project_root" && pwd)"
    
    # Create logs directory and setup log file
    mkdir -p "$project_root/logs"
    setup_log_file="$(realpath "$project_root")/logs/setup_${timestamp}.log"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] BBH Framework Setup Started" > "$setup_log_file"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] ========================================" >> "$setup_log_file"
    print_info "Setup log: $setup_log_file"

    # Check uv
    log_msg "INFO" "Checking uv installation..."
    if ! command -v uv &> /dev/null; then
        log_msg "ERROR" "uv package manager not found"
        print_error "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    log_msg "INFO" "uv package manager found"
    print_success "uv found"

    # Load .env
    local api_key_configured=false
    log_msg "INFO" "Loading environment variables..."
    if [ -f "$project_root/.env" ]; then
        source "$project_root/.env"
        log_msg "INFO" ".env file loaded successfully"
        print_success ".env loaded"
        if [ -n "$OPENAI_API_KEY" ]; then
            log_msg "INFO" "OpenAI API key found and configured"
            print_success "OpenAI API key configured"
            api_key_configured=true
        else
            log_msg "WARN" "OpenAI API key not set in environment"
        fi
    else
        log_msg "WARN" ".env file not found in project root"
        print_warning ".env file not found"
        print_info "Create one with: echo 'OPENAI_API_KEY=your-key' > .env"
    fi

    # Setup root project
    echo
    log_msg "INFO" "Starting root project setup..."
    print_info "Setting up root project..."
    cd "$project_root"
    
    log_msg "INFO" "Running uv sync for root project..."
    if uv sync >> "$setup_log_file" 2>&1; then
        log_msg "INFO" "Root project setup completed successfully"
        print_success "Root project ready"
    else
        log_msg "ERROR" "Root project setup failed"
        print_error "Root project setup failed"
        exit 1
    fi

    # Setup frameworks
    echo
    log_msg "INFO" "Starting framework scanning..."
    print_info "Scanning frameworks..."
    cd frameworks
    
    local setup_count=0
    local ready_frameworks=()
    local disabled_frameworks=()
    local no_setup_frameworks=()
    local failed_frameworks=()
    
    # Find frameworks with setup = "ready"
    for framework_dir in fm_*; do
        if [ -d "$framework_dir" ]; then
            if [ -f "$framework_dir/setup.sh" ] && [ -f "$framework_dir/pyproject.toml" ]; then
                local setup_status=$(grep "^setup = " "$framework_dir/pyproject.toml" 2>/dev/null | cut -d'"' -f2)
                if [ "$setup_status" = "ready" ]; then
                    ready_frameworks+=("$framework_dir")
                else
                    disabled_frameworks+=("$framework_dir")
                fi
            else
                no_setup_frameworks+=("$framework_dir")
            fi
        fi
    done
    
    # Show framework status summary
    echo
    print_info "Framework Status Summary:"
    print_success "Ready for setup: ${#ready_frameworks[@]} frameworks"
    for fw in "${ready_frameworks[@]}"; do
        echo "  ✓ $fw"
    done
    
    if [ ${#disabled_frameworks[@]} -gt 0 ]; then
        echo
        print_warning "Disabled/Not Ready: ${#disabled_frameworks[@]} frameworks"
        for fw in "${disabled_frameworks[@]}"; do
            local setup_status=$(grep "^setup = " "$fw/pyproject.toml" 2>/dev/null | cut -d'"' -f2)
            echo "  ⏸ $fw (setup = \"$setup_status\")"
        done
    fi
    
    if [ ${#no_setup_frameworks[@]} -gt 0 ]; then
        echo
        print_info "No setup script: ${#no_setup_frameworks[@]} frameworks"
        for fw in "${no_setup_frameworks[@]}"; do
            echo "  ○ $fw"
        done
    fi
    
    if [ ${#ready_frameworks[@]} -gt 0 ]; then
        echo
        read -p "Setup all ${#ready_frameworks[@]} ready frameworks? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo
            print_info "Setting up frameworks..."
            
            for framework_dir in "${ready_frameworks[@]}"; do
                print_info "Setting up $framework_dir..."
                cd "$framework_dir"
                
                # Log framework setup start
                log_msg "INFO" "========================================="
                log_msg "INFO" "Starting $framework_dir setup"
                log_msg "INFO" "========================================="
                
                # Capture setup output to temp file for error handling while streaming to main log
                local temp_log="/tmp/${framework_dir}_setup.log"
                
                # Run setup and capture both output and exit status
                set +e  # Temporarily disable exit on error
                ./setup.sh > "$temp_log" 2>&1
                local setup_exit_code=$?
                set -e  # Re-enable exit on error
                
                # Stream the output to main log with timestamps
                while IFS= read -r line; do
                    echo "$(date '+%Y-%m-%d %H:%M:%S') [SETUP] [$framework_dir] $line" >> "$setup_log_file"
                done < "$temp_log"
                
                # Check exit status
                if [ $setup_exit_code -eq 0 ]; then
                    log_msg "INFO" "$framework_dir setup completed successfully"
                    log_msg "INFO" "========================================="
                    print_success "$framework_dir setup complete"
                    setup_count=$((setup_count + 1))
                    rm -f "$temp_log"  # Clean up successful temp logs
                else
                    log_msg "ERROR" "$framework_dir setup FAILED (exit code: $setup_exit_code)"
                    log_msg "ERROR" "========================================="
                    print_error "$framework_dir setup failed"
                    failed_frameworks+=("$framework_dir:$temp_log")
                fi
                cd ..
            done
            
            # Show detailed failure summary
            if [ ${#failed_frameworks[@]} -gt 0 ]; then
                echo
                print_error "Setup Failed Summary:"
                print_error "${#failed_frameworks[@]} framework(s) failed setup"
                
                for entry in "${failed_frameworks[@]}"; do
                    local fw="${entry%:*}"
                    local temp_log="${entry#*:}"
                    echo
                    print_error "=== $fw - Last 10 lines of error log ==="
                    if [ -f "$temp_log" ]; then
                        tail -n 10 "$temp_log" | sed 's/^/  /'
                        rm -f "$temp_log"  # Clean up temp log after showing
                    else
                        echo "  Error log not found"
                    fi
                done
                echo
                print_info "Full logs available in: $setup_log_file"
            fi
        else
            print_info "Framework setup skipped"
        fi
    else
        print_warning "No frameworks ready for setup"
    fi
    
    cd "$project_root"
    
    # Summary
    echo
    log_msg "INFO" "Framework setup phase completed"
    log_msg "INFO" "Successfully set up: $setup_count frameworks"
    log_msg "INFO" "Failed setups: ${#failed_frameworks[@]} frameworks"
    
    if [ ${#failed_frameworks[@]} -gt 0 ]; then
        print_warning "Framework setup complete with ${#failed_frameworks[@]} failures"
        print_success "Successfully set up: $setup_count frameworks"
        print_error "Failed to set up: ${#failed_frameworks[@]} frameworks"
    else
        print_success "Framework setup complete ($setup_count frameworks)"
    fi

    # Create config
    log_msg "INFO" "Creating .run_config file..."
    cat > .run_config << EOF
{
  "setup_complete": true,
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "api_key_configured": $api_key_configured,
  "frameworks_setup_count": $setup_count,
  "frameworks_failed_count": ${#failed_frameworks[@]}
}
EOF

    log_msg "INFO" ".run_config file created successfully"
    print_success ".run_config created"
    
    echo
    log_msg "INFO" "BBH Framework Setup completed"
    log_msg "INFO" "Setup log file: $setup_log_file"
    
    print_success "Setup complete!"
    print_info "Successfully set up: $setup_count frameworks"
    if [ ${#failed_frameworks[@]} -gt 0 ]; then
        print_warning "Failed setups: ${#failed_frameworks[@]} frameworks"
    fi
    print_info "Setup log: $setup_log_file"
    print_info "Next steps:"
    print_info "  1. Run './run.sh' for evaluation"
    print_info "  2. Check failed frameworks and retry setup if needed"
}

main "$@"