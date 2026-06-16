#!/bin/bash
#
# Talos Engine - Disk Alert
#
# Runs every 6 hours via cron to check disk usage and alert
# if above threshold. Quiet when healthy.
#
# Usage:
#   0 */6 * * * /path/to/scripts/disk_alert.sh
#

THRESHOLD=85
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$DISK_USAGE" -ge "$THRESHOLD" ]; then
    echo "🚨 DISK ALERT: Usage at ${DISK_USAGE}% (threshold: ${THRESHOLD}%)"

    # Show top disk-consuming directories
    echo ""
    echo "Top directories by size:"
    du -sh /* 2>/dev/null | sort -rh | head -10

    # Log to error file
    TIMESTAMP=$(date -Iseconds)
    echo "{\"timestamp\":\"$TIMESTAMP\",\"level\":2,\"source\":\"disk_alert\",\"message\":\"Disk usage at ${DISK_USAGE}%\",\"details\":{\"disk_pct\":$DISK_USAGE}}" \
        >> data/errors.jsonl 2>/dev/null || true

    exit 1
fi

# Healthy - no output
exit 0
