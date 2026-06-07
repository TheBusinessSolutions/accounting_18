#!/bin/bash
# ==============================================================================
# UNIVERSAL AUTOMATED UPSTREAM PULL SCRIPT
# This script auto-detects all mapped remotes and merges them side-by-side.
# ==============================================================================

TARGET_BRANCH="18.0" # Change this to 19.0 next year when moving to Odoo 19

echo "=========================================="
echo "🛡️  STEP 1: CHECKING WORKSPACE SAFETY"
echo "=========================================="

# Guardrail: Check if developer has uncommitted local translations/custom code
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ ERROR: Your working tree is not clean!"
    echo "Please commit your Egyptian local translations and custom code in GitHub Desktop first."
    exit 1
fi
echo "✅ Workspace is clean. Proceeding safely."

echo "=========================================="
echo "🚀 STEP 2: SYNCING ALL REGISTERED UPSTREAMS"
echo "=========================================="
git fetch --all

# Automatically extracts all mapped nicknames except our own 'origin' cloud
REMOTES=$(git remote | grep -v '^origin$')

if [ -z "$REMOTES" ]; then
    echo "⚠️  WARNING: No upstream remotes found! Did you run ./init_remotes.sh first?"
    exit 0
fi

echo "=========================================="
echo "🔀 STEP 3: AUTO-MERGING LAYERS SIDE-BY-SIDE"
echo "=========================================="
for REMOTE in $REMOTES
do
    echo "--------------------------------------------------------"
    echo "📦 Processing updates for: $REMOTE..."
    
    # Universal loop that executes the merge without hardcoding individual names
    git merge "$REMOTE/$TARGET_BRANCH" --allow-unrelated-histories -m "Auto-sync $REMOTE $TARGET_BRANCH updates"
done

echo "========================================================"
echo "🎯 STEP 4: VERIFICATION & DEPLOYMENT"
echo "========================================================"
echo "Process finished! Please check GitHub Desktop right now to:"
echo " 1. Choose 'Use modified file from main' for any config file conflicts."
echo " 2. Click 'Commit Merge' and 'Push Origin' to sync to our cloud."
echo " 3. On your client's server, run your standard 'sudo git pull' to deploy!"
echo "========================================================"

