#!/bin/bash
# ==============================================================================
# ENVIRONMENT SETUP SCRIPT: MAP UPSTREAM REMOTES
# Run this ONCE when cloning this repository to a new machine.
# ==============================================================================

echo "=========================================="
echo "🔗 STEP 1: INITIALIZING ENVIRONMENT BRIDGES"
echo "=========================================="

# ------------------------------------------------------------------------------
# ⚠️ TEAM INSTRUCTION: Add your custom remote mapping lines below.
# Syntax: git remote add [nickname] [github_url] 2>/dev/null
# ------------------------------------------------------------------------------

git remote add oca_agreement https://github.com/OCA/agreement.git 2>/dev/null
git remote add upstream_source_oca_reconcile https://github.com/OCA/account-reconcile.git 2>/dev/null
git remote add account-financial-tools https://github.com/OCA/account-financial-tools.git 2>/dev/null
git remote add account-invoicing https://github.com/OCA/account-invoicing.git 2>/dev/null
git remote add account-payment https://github.com/OCA/account-payment.git 2>/dev/null
git remote add contract https://github.com/OCA/contract.git 2>/dev/null
# ------------------------------------------------------------------------------

echo "✅ Git remote links mapped successfully!"
echo "👉 You can now safely run './pull_updates.sh' to download the code."

