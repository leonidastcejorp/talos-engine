#!/bin/bash
#
# Talos Engine - VPS Config Backup
#
# Creates a weekly backup of critical configuration files
# and Hermes Agent state. Stores in a timestamped archive.
#
# Usage:
#   0 2 * * 0 /path/to/scripts/vps_backup.sh
#
# Set BACKUP_DIR to your preferred backup location.
#

set -euo pipefail

BACKUP_DIR="${HOME}/backups"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="talos_backup_${DATE_STAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
KEEP_DAYS=90  # Retain backups for 90 days

echo "📦 Talos Engine - Configuration Backup"
echo "   Date: ${DATE_STAMP}"
echo "   Destination: ${BACKUP_PATH}"
echo ""

# Create backup directory
mkdir -p "${BACKUP_PATH}"

# ─── Backup Hermes Agent Configs ──────────────────────────────────────────
if [ -d "${HOME}/.hermes" ]; then
    echo "   📋 Backing up Hermes Agent config..."
    mkdir -p "${BACKUP_PATH}/hermes"
    cp -r "${HOME}/.hermes/config.yaml" "${BACKUP_PATH}/hermes/" 2>/dev/null || true
    cp -r "${HOME}/.hermes/SOUL.md" "${BACKUP_PATH}/hermes/" 2>/dev/null || true
    cp -r "${HOME}/.hermes/cron" "${BACKUP_PATH}/hermes/" 2>/dev/null || true
    cp -r "${HOME}/.hermes/skills" "${BACKUP_PATH}/hermes/" 2>/dev/null || true
    cp -r "${HOME}/.hermes/plugins" "${BACKUP_PATH}/hermes/" 2>/dev/null || true
fi

# ─── Backup Talos Engine Repo ──────────────────────────────────────────────
if [ -d "${HOME}/repos/talos-engine" ]; then
    echo "   📋 Backing up talos-engine repo..."
    mkdir -p "${BACKUP_PATH}/talos-engine"

    # Back up configs and data (not venv/node_modules)
    cp -r "${HOME}/repos/talos-engine/flowcore/config" "${BACKUP_PATH}/talos-engine/" 2>/dev/null || true
    cp -r "${HOME}/repos/talos-engine/hermes" "${BACKUP_PATH}/talos-engine/" 2>/dev/null || true
    cp -r "${HOME}/repos/talos-engine/data" "${BACKUP_PATH}/talos-engine/" 2>/dev/null || true
    cp -r "${HOME}/repos/talos-engine/scripts" "${BACKUP_PATH}/talos-engine/" 2>/dev/null || true
fi

# ─── Backup SSH Configs ────────────────────────────────────────────────────
if [ -d "${HOME}/.ssh" ]; then
    echo "   📋 Backing up SSH config..."
    mkdir -p "${BACKUP_PATH}/ssh"
    cp "${HOME}/.ssh/config" "${BACKUP_PATH}/ssh/" 2>/dev/null || true
    cp "${HOME}/.ssh/authorized_keys" "${BACKUP_PATH}/ssh/" 2>/dev/null || true
fi

# ─── Backup Crontab ────────────────────────────────────────────────────────
echo "   📋 Backing up crontab..."
crontab -l > "${BACKUP_PATH}/crontab.txt" 2>/dev/null || echo "   (no crontab)"

# ─── Create Archive ────────────────────────────────────────────────────────
echo ""
echo "   📦 Creating archive..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_PATH}"

ARCHIVE_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
echo "   ✅ Backup created: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz (${ARCHIVE_SIZE})"

# ─── Clean Old Backups ─────────────────────────────────────────────────────
if [ "${KEEP_DAYS}" -gt 0 ]; then
    echo ""
    echo "   🧹 Cleaning backups older than ${KEEP_DAYS} days..."
    find "${BACKUP_DIR}" -name "talos_backup_*.tar.gz" -mtime +"${KEEP_DAYS}" -delete 2>/dev/null || true
fi

echo ""
echo "🏁 Backup complete."
