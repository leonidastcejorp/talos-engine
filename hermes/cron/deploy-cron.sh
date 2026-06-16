#!/bin/bash
#
# Talos Engine - Cron Job Deployer
#
# Deploys all monitoring and automation cron jobs to Hermes Agent
# using 'hermes cron create' for each job defined in jobs.json.
#
# Usage:
#   bash hermes/cron/deploy-cron.sh
#   bash hermes/cron/deploy-cron.sh --dry-run
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOBS_FILE="${SCRIPT_DIR}/jobs.json"
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--dry-run]"
            exit 1
            ;;
    esac
done

if [ ! -f "$JOBS_FILE" ]; then
    echo "❌ Jobs file not found: ${JOBS_FILE}"
    exit 1
fi

echo "🕐 Talos Engine - Cron Deployer"
echo "   Jobs file: ${JOBS_FILE}"
echo ""

# Check if hermes CLI is available
if ! command -v hermes &> /dev/null; then
    echo "❌ Hermes Agent CLI not found. Install with: pip install hermes-agent"
    exit 1
fi

# Parse and deploy each job
DEPLOYED=0
FAILED=0

# Read jobs from JSON using Python (more reliable than jq)
python3 -c "
import json, sys

with open('${JOBS_FILE}') as f:
    jobs = json.load(f)

for job in jobs['jobs']:
    name = job['name']
    schedule = job['schedule']
    command = job['command']
    description = job.get('description', '')
    print(f'{name}|{schedule}|{command}|{description}')
" | while IFS='|' read -r name schedule command description; do
    if [ -z "$name" ]; then
        continue
    fi

    echo "   📋 Deploying: ${name}"
    echo "      Schedule: ${schedule}"
    echo "      Command: ${command}"

    if [ "$DRY_RUN" = false ]; then
        if hermes cron create \
            --name "$name" \
            --schedule "$schedule" \
            --command "$command" \
            --description "$description" 2>/dev/null; then
            echo "      ✅ Deployed"
            DEPLOYED=$((DEPLOYED + 1))
        else
            echo "      ❌ Failed"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "      [DRY RUN] Would deploy"
    fi
    echo ""
done

echo "🏁 Deployment complete."
if [ "$DRY_RUN" = false ]; then
    echo "   Deployed: ${DEPLOYED:-0} | Failed: ${FAILED:-0}"
fi
echo ""
echo "Verify with: hermes cron list"
