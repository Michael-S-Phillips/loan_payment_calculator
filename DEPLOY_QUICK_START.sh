#!/bin/bash
# Quick start script for Heroku deployment
# This script automates most of the deployment process

set -e  # Exit on any error

echo "🚀 Loan Payment Calculator - Heroku Deployment Helper"
echo "========================================================"
echo ""

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found. Please install it first:"
    echo "   macOS: brew install heroku/brew/heroku"
    echo "   Windows/Linux: Visit https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

echo "✅ Heroku CLI found: $(heroku --version)"
echo ""

# Check if logged in
if ! heroku auth:whoami > /dev/null 2>&1; then
    echo "⚠️  You're not logged in to Heroku. Logging in now..."
    heroku login
else
    echo "✅ Already logged in as: $(heroku auth:whoami)"
fi

echo ""
echo "Step 1: Checking git status..."
if ! git status > /dev/null 2>&1; then
    echo "❌ Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  You have uncommitted changes. Committing them now..."
    git add -A
    read -p "Enter commit message [Heroku deployment config]: " commit_msg
    commit_msg=${commit_msg:-"Heroku deployment config"}
    git commit -m "$commit_msg"
else
    echo "✅ All changes are committed"
fi

echo ""
echo "Step 2: Creating Heroku app..."
read -p "Enter app name (lowercase, hyphens OK) [loan-calculator]: " app_name
app_name=${app_name:-"loan-calculator"}

if heroku create "$app_name" 2>&1 | grep -q "already exists"; then
    echo "⚠️  App already exists. Using existing app: $app_name"
    git remote remove heroku 2>/dev/null || true
    heroku git:remote -a "$app_name"
else
    echo "✅ Created Heroku app: $app_name"
fi

echo ""
echo "Step 3: Adding buildpacks..."
heroku buildpacks:add --index 1 heroku-community/apt -a "$app_name"
heroku buildpacks:add --index 2 heroku/python -a "$app_name"
echo "✅ Buildpacks added"

echo ""
echo "Step 4: Showing buildpacks..."
heroku buildpacks -a "$app_name"

echo ""
echo "Step 5: Deploying to Heroku (this takes 2-5 minutes)..."
echo "Watch for 'State changed from starting to up' in the logs"
echo ""
git push heroku main

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Your app is now live at:"
echo "   https://$app_name.herokuapp.com"
echo ""
echo "To open it in your browser, run:"
echo "   heroku open -a $app_name"
echo ""
echo "To view logs, run:"
echo "   heroku logs --tail -a $app_name"
echo ""
echo "📖 For more help, read: DEPLOYMENT.md"
