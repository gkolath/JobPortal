#!/bin/bash
# Deploy helper for Railway
set -e

echo "=== Job Portal Railway Deploy ==="
echo ""
echo "Prerequisites:"
echo "  1. Railway account: https://railway.app"
echo "  2. Adzuna API keys: https://developer.adzuna.com"
echo ""
echo "Steps:"
echo "  1. railway login"
echo "  2. railway init          # create new project"
echo "  3. railway add --database postgres"
echo "  4. railway variables set JWT_SECRET=\$(openssl rand -hex 32)"
echo "  5. railway variables set ADZUNA_APP_ID=your_id"
echo "  6. railway variables set ADZUNA_APP_KEY=your_key"
echo "  7. railway variables set RUN_SEED=1   # first deploy only"
echo "  8. railway up"
echo "  9. railway domain       # get HTTPS URL to share"
echo ""
echo "After first deploy, unset RUN_SEED:"
echo "  railway variables delete RUN_SEED"
