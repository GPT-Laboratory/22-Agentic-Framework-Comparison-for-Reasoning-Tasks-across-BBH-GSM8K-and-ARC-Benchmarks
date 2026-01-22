#!/bin/bash

set -e

# Cleanup definitions: "name|patterns|exclusions|description|dangerous"
CLEANUP_DEFS=(
    "venv|.venv||Virtual environments|no"
    "node|node_modules|.yarn,node_modules/*|Node.js packages|no" 
    "yarn|.yarn|node_modules,.venv|Yarn cache|no"
    "cache|__pycache__,*.pyc|node_modules,.yarn,.venv|Python cache|no"
    "build|build,dist,*.egg-info,.eggs,.tox|node_modules,.yarn,.venv|Build artifacts|no"
    "docker|docker-compose.yml,docker-compose.yaml|node_modules,.yarn,.venv|Docker containers|no"
    "outputs|outputs||Framework evaluation results|yes"
    "temp|*.tmp,*.temp,.DS_Store|node_modules,.yarn,.venv|Temporary files|no"
    "logs|*.log|node_modules,.yarn,.venv|Large log files|no"
)

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# Build exclusions for find command
build_exclusions() {
    local exclusions="$1"
    [ -z "$exclusions" ] && return
    
    local result=""
    IFS=',' read -ra EXCL <<< "$exclusions"
    for excl in "${EXCL[@]}"; do
        result="$result -path '*/$excl' -prune -o"
    done
    result="${result% -o}"  # Remove trailing -o
    echo -e "\\( $result \\) -prune -o"
}

# Build patterns for find command  
build_patterns() {
    local patterns="$1"
    local result=""
    IFS=',' read -ra PATT <<< "$patterns"
    for i in "${!PATT[@]}"; do
        [ $i -gt 0 ] && result="$result -o"
        result="$result -name '${PATT[i]}'"
    done
    echo -e "\\( $result \\)"
}

# Calculate total size of found items
calc_size() {
    local items="$1"
    [ -z "$items" ] && echo -e "0B" && return
    echo -e "$items" | xargs du -sb 2>/dev/null | awk '{s+=$1} END {
        if(s>=1073741824) printf "%.1fG", s/1073741824
        else if(s>=1048576) printf "%.1fM", s/1048576  
        else if(s>=1024) printf "%.1fK", s/1024
        else printf "%dB", s
    }' || echo -e "unknown"
}


# Clean a single item type
cleanup_item() {
    local def="$1"
    IFS='|' read -r name patterns exclusions desc dangerous <<< "$def"
    
    # Skip if target specified and doesn't match
    if [ -n "$TARGET" ] && [ "$TARGET" != "$name" ] && [ "$TARGET" != "all" ]; then
        return
    fi
    
    echo -e "\n${BLUE}▶ Scanning for $desc...${NC}"
    
    # Build and execute find command
    local excl_part=$(build_exclusions "$exclusions")
    local patt_part=$(build_patterns "$patterns")
    local find_cmd="find $SEARCH_PATH $excl_part $patt_part -print 2>/dev/null"
    local items=$(eval "$find_cmd")
    
    if [ -z "$items" ]; then
        echo -e "  ${GREEN}✓ No items found${NC}"
        return
    fi
    
    # Show results
    local count=$(echo -e "$items" | wc -l)
    local size=$(calc_size "$items")
    echo -e "  ${YELLOW}Found: $count items ($size total)${NC}"
    
    # Show sample (first 3 items)
    echo -e "$items" | head -3 | sed 's/^/    /'
    [ $count -gt 3 ] && echo -e "    ... and $((count-3)) more"
    
    # Confirm deletion
    [ "$dangerous" = "yes" ] && echo -e "  ${RED}⚠️  WARNING: This will delete evaluation results!${NC}"
    
    echo -e "${YELLOW}Delete these $desc? (y/N):${NC} \c"
    read -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ "$name" = "docker" ] && command -v docker >/dev/null 2>&1; then
            # For Docker: handle both compose files and standalone containers
            echo -e "$items" | while read -r compose_file; do
                [ -f "$compose_file" ] && (cd "$(dirname "$compose_file")" && docker compose down --volumes --remove-orphans 2>/dev/null) || true
            done
            
            # Handle standalone containers with framework-specific naming patterns
            echo -e "  ${BLUE}Checking for standalone framework containers...${NC}"
            framework_containers=$(docker ps --filter "name=letta-bbh-server" --filter "name=fm_" --filter "name=bbh-" --format "{{.Names}}" 2>/dev/null || true)
            
            if [ -n "$framework_containers" ]; then
                echo -e "  ${YELLOW}Found standalone containers:${NC}"
                echo -e "$framework_containers" | sed 's/^/    /'
                echo -e "${YELLOW}Stop and remove these containers? (y/N):${NC} \\c"
                read -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    echo -e "$framework_containers" | xargs -r docker stop
                    echo -e "$framework_containers" | xargs -r docker rm
                    echo -e "  ${GREEN}✓ Stopped and removed standalone containers${NC}"
                fi
            else
                echo -e "  ${GREEN}✓ No standalone framework containers found${NC}"
            fi
            
            echo -e "  ${GREEN}✓ Docker cleanup complete${NC}"
        else
            # For other types: delete the files
            echo -e "$items" | xargs rm -rf 2>/dev/null || true
            echo -e "  ${GREEN}✓ Deleted $count items ($size freed)${NC}"
        fi
    else
        echo -e "  ${GREEN}○ Skipped${NC}"
    fi
}

# Show help
show_help() {
    echo -e "Usage: $0 [path] [target]"
    echo -e "  path   - Directory to scan (default: current)"
    echo -e "  target - Specific item to clean (venv|node|yarn|cache|build|docker|outputs|temp|logs|all)"
    echo -e ""
    echo -e "Examples:"
    echo -e "  $0                    # Interactive cleanup of current directory"
    echo -e "  $0 ./frameworks       # Clean frameworks directory"
    echo -e "  $0 . node            # Clean only node_modules"
    echo -e "  $0 . all             # Clean everything without prompting each type"
}

# Parse arguments
case "$1" in
    -h|--help) show_help; exit 0 ;;
esac

SEARCH_PATH="${1:-.}"
TARGET="$2"

# Validate search path
if [ ! -d "$SEARCH_PATH" ]; then
    echo -e "${RED}Error: Directory '$SEARCH_PATH' does not exist${NC}"
    exit 1
fi

# Main execution
echo -e "${GREEN}=== BBH Project Cleanup ===${NC}"
echo -e "Scanning: $SEARCH_PATH"
[ -n "$TARGET" ] && echo -e "Target: $TARGET"

for def in "${CLEANUP_DEFS[@]}"; do
    cleanup_item "$def"
done

echo -e "\n${GREEN}✓ Cleanup complete!${NC}"
