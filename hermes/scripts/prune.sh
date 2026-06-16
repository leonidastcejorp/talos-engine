#!/bin/bash
#
# Talos Engine - Session Cleanup
#
# Removes Hermes Agent session data older than 30 days.
# Designed for weekly cron: 0 3 * * 0 /path/to/scripts/prune.sh
#
# Usage:
#   bash scripts/prune.sh
#   bash scripts/prune.sh --days 60
#

set -euo pipefail

DAYS=30
HERMES_DIR="${HOME}/.hermes"
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--days N] [--dry-run]"
            exit 1
            ;;
    esac
done

echo "🧹 Talos Engine - Session Cleanup"
echo "   Max age: ${DAYS} days"
echo "   Hermes dir: ${HERMES_DIR}"
echo ""

if [ ! -d "$HERMES_DIR" ]; then
    echo "⚠️ Hermes directory not found at ${HERMES_DIR}"
    exit 0
fi

# Find and delete old session data
DELETED_COUNT=0
FREED_BYTES=0

# Clean conversations older than N days
if [ -d "${HERMES_DIR}/conversations" ]; then
    while IFS= read -r -d '' file; do
        if [ "$DRY_RUN" = true ]; then
            echo "   [DRY RUN] Would delete: ${file}"
        else
            FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo 0)
            rm -f "$file"
            DELETED_COUNT=$((DELETED_COUNT + 1))
            FREED_BYTES=$((FREED_BYTES + FILE_SIZE))
        fi
    done < <(find "${HERMES_DIR}/conversations" -type f -mtime +"${DAYS}" -print0 2>/dev/null)
fi

# Clean old logs
if [ -d "${HERMES_DIR}/logs" ]; then
    while IFS= read -r -d '' file; do
        if [ "$DRY_RUN" = true ]; then
            echo "   [DRY RUN] Would delete: ${file}"
        else
            FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo 0)
            rm -f "$file"
            DELETED_COUNT=$((DELETED_COUNT + 1))
            FREED_BYTES=$((FREED_BYTES + FILE_SIZE))
        fi
    done < <(find "${HERMES_DIR}/logs" -type f -mtime +"${DAYS}" -print0 2>/dev/null)
fi

# Clean old state data
if [ -d "${HERMES_DIR}/state" ]; then
    while IFS= read -r -d '' file; do
        if [ "$DRY_RUN" = true ]; then
            echo "   [DRY RUN] Would delete: ${file}"
        else
            FILE_SIZE=$(stat -c%s "$file" 2>/dev/null || echo 0)
            rm -f "$file"
            DELETED_COUNT=$((DELETED_COUNT + 1))
            FREED_BYTES=$((FREED_BYTES + FILE_SIZE))
        fi
    done < <(find "${HERMES_DIR}/state" -type f -mtime +"${DAYS}" -print0 2>/dev/null)
fi

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "🏁 Dry run complete. Use without --dry-run to actually delete."
else
    FREED_MB=$(echo "scale=2; ${FREED_BYTES} / 1048576" | bc 2>/dev/null || echo "0")
    echo "✅ Deleted ${DELETED_COUNT} files (freed ~${FREED_MB} MB)"
fi
