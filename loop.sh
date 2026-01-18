#!/bin/bash
# Ralph Loop for Orion Trading Signals Platform
# Usage: ./loop.sh [plan] [max_iterations]
# Examples:
#   ./loop.sh              # Build mode, unlimited iterations
#   ./loop.sh 20           # Build mode, max 20 iterations
#   ./loop.sh plan         # Plan mode, unlimited iterations
#   ./loop.sh plan 5       # Plan mode, max 5 iterations

set -euo pipefail

# Parse arguments
if [ "$1" = "plan" ]; then
    # Plan mode
    MODE="plan"
    PROMPT_FILE="PROMPT_plan.md"
    MAX_ITERATIONS=${2:-0}
elif [[ "$1" =~ ^[0-9]+$ ]]; then
    # Build mode with max iterations
    MODE="build"
    PROMPT_FILE="PROMPT_build.md"
    MAX_ITERATIONS=$1
else
    # Build mode, unlimited
    MODE="build"
    PROMPT_FILE="PROMPT_build.md"
    MAX_ITERATIONS=0
fi

ITERATION=0
CURRENT_BRANCH=$(git branch --show-current)
LOG_FILE="ralph_${MODE}_$(date +%Y%m%d_%H%M%S).log"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Mode:   $MODE"
echo "Prompt: $PROMPT_FILE"
echo "Branch: $CURRENT_BRANCH"
echo "Log:    $LOG_FILE"
[ $MAX_ITERATIONS -gt 0 ] && echo "Max:    $MAX_ITERATIONS iterations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verify prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "Error: $PROMPT_FILE not found"
    exit 1
fi

# Main loop
while true; do
    if [ $MAX_ITERATIONS -gt 0 ] && [ $ITERATION -ge $MAX_ITERATIONS ]; then
        echo "Reached max iterations: $MAX_ITERATIONS" | tee -a "$LOG_FILE"
        break
    fi

    echo "======================== LOOP $((ITERATION + 1)) ========================" | tee -a "$LOG_FILE"
    echo "Started at $(date)" | tee -a "$LOG_FILE"

    # Run Ralph iteration
    # -p: Headless mode (non-interactive, reads from stdin)
    # --dangerously-skip-permissions: Auto-approve all tool calls (YOLO mode)
    # --output-format=stream-json: Structured output for logging
    # --model opus: Primary agent uses Opus for complex reasoning
    # --verbose: Detailed execution logging
    if cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --output-format=stream-json \
        --model opus \
        --verbose 2>&1 | tee -a "$LOG_FILE"; then

        # Push changes after successful iteration
        echo "Pushing to remote..." | tee -a "$LOG_FILE"
        git push origin "$CURRENT_BRANCH" 2>&1 || {
            echo "Failed to push. Creating remote branch..." | tee -a "$LOG_FILE"
            git push -u origin "$CURRENT_BRANCH" 2>&1 || true
        }
    else
        echo "Iteration failed with exit code $?" | tee -a "$LOG_FILE"
    fi

    ITERATION=$((ITERATION + 1))
    echo -e "\n\n======================== LOOP $ITERATION COMPLETE ========================" | tee -a "$LOG_FILE"
    echo "Finished at $(date)" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "Ralph loop completed" | tee -a "$LOG_FILE"
echo "Total iterations: $ITERATION" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
