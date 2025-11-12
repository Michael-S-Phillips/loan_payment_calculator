# Heroku Deployment Guide

A complete step-by-step guide for deploying the Loan Payment Calculator to Heroku. This is your first deployment - we'll take it slow and explain everything!

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Heroku Account Setup](#heroku-account-setup)
3. [Deployment Steps](#deployment-steps)
4. [Troubleshooting](#troubleshooting)
5. [After Deployment](#after-deployment)

---

## Prerequisites

Before you start, you need to have:

- ✅ **Git installed** (you already have this)
- ✅ **GitHub account** (you already have this - your repo is on GitHub)
- ✅ **A Heroku account** (we'll create this in Step 1)
- ✅ **Heroku CLI** (command-line tool - we'll install this in Step 2)

---

## Heroku Account Setup

### Step 1: Create a Heroku Account

1. Go to https://signup.heroku.com/
2. Fill in the form:
   - Email: Use your personal email
   - First name: Your first name
   - Last name: Your last name
   - Company (optional): Your company name or leave blank
   - Primary language: Node.js (doesn't matter, we're using Python)
3. Click "Create Free Account"
4. Check your email for a verification link and click it
5. Create a password and click "Set Password and Log In"

**You now have a Heroku account!** 🎉

---

## Deployment Steps

### Step 2: Install Heroku CLI

The Heroku CLI is a command-line tool that lets you manage your apps from the terminal.

**On macOS:**
```bash
brew install heroku/brew/heroku
```

**Verify installation:**
```bash
heroku --version
```

You should see something like: `heroku/7.68.0 darwin-x64 node-v18.x`

### Step 3: Login to Heroku from Your Terminal

```bash
heroku login
```

This will:
1. Open a browser window
2. Ask you to click "Log In"
3. Return you to the terminal (authenticated)

**You should see a message like:**
```
Logged in as your-email@example.com
```

### Step 4: Create a Heroku App

Go to your loan calculator directory and create a new Heroku app:

```bash
cd /Users/phillipsm/Documents/Professional/LoanPaymentCalculator
heroku create your-app-name
```

**Important:** Replace `your-app-name` with a unique name (lowercase, hyphens only):
- Good examples: `loan-calculator-michael`, `michael-loan-calc`
- Bad examples: `LoanCalculator` (has uppercase), `loan_calculator` (has underscore)

**You should see:**
```
Creating ⬢ your-app-name... done
https://your-app-name.herokuapp.com/ | https://git.heroku.com/your-app-name.git
```

**Save that URL!** That's where your app will live.

### Step 5: Add Required Buildpacks

Buildpacks are like plugins that help Heroku build your app. You need:
1. **APT buildpack** - to install system packages (CBC solver)
2. **Python buildpack** - for Python packages

```bash
heroku buildpacks:add --index 1 heroku-community/apt
heroku buildpacks:add --index 2 heroku/python
```

**Verify they were added:**
```bash
heroku buildpacks
```

You should see:
```
1. heroku-community/apt
2. heroku/python
```

### Step 6: Commit and Push to Heroku

Now you'll deploy your code to Heroku. First, make sure everything is committed to git:

```bash
git add -A
git status
```

You should see:
- `Procfile` (new)
- `runtime.txt` (new)
- `Aptfile` (new)
- `DEPLOYMENT.md` (new)

Commit these files:

```bash
git commit -m "Add Heroku deployment configuration (Procfile, runtime.txt, Aptfile)"
```

Now deploy to Heroku:

```bash
git push heroku main
```

This will:
1. Send your code to Heroku
2. Install Python dependencies
3. Install system packages (CBC solver)
4. Start your app

**This takes 2-5 minutes.** You'll see lots of output - this is normal!

### Step 7: Verify Your Deployment

Check that the app is running:

```bash
heroku logs --tail
```

This shows you the live logs. Look for:
- ✅ `State changed from starting to up` - Success!
- ❌ `State changed from starting to crashed` - Something went wrong

If it crashed, the logs will show the error. We'll troubleshoot in the Troubleshooting section.

If it's running, visit your app:

```bash
heroku open
```

This opens your app in your browser! You should see the Loan Payment Calculator web interface.

---

## Troubleshooting

### "Build failed" or "Slug too large"

**Problem:** Your app is too big or has too many dependencies.

**Solution:**
1. Check what went wrong:
   ```bash
   heroku logs --tail
   ```

2. The most common issue is the CBC solver taking up space. Try building without it first:
   - Remove the `Aptfile`
   - Push again: `git push heroku main`
   - This will let you test if the Streamlit app works

### "Application error" (App crashes when you visit it)

**Problem:** The app starts but crashes when you try to use it.

**Solution:**
1. Check the logs:
   ```bash
   heroku logs --tail -n 100
   ```

2. Look for error messages like:
   - `ModuleNotFoundError` - A Python package is missing
   - `FileNotFoundError` - A file is missing
   - Memory errors - The app ran out of memory

3. For most issues:
   ```bash
   # Restart the app
   heroku restart

   # Rebuild from scratch
   heroku rebuild
   ```

### "Permission denied" or "authentication failed"

**Problem:** Heroku CLI can't authenticate.

**Solution:**
```bash
# Log in again
heroku login

# Verify you're logged in
heroku auth:whoami
```

### App starts but pages are blank/slow

**Problem:** This is normal for the first load - Streamlit takes time to initialize.

**Solution:** Wait 30 seconds and refresh the page. If it's still blank after 2 minutes, check logs:
```bash
heroku logs --tail
```

---

## After Deployment

### Great! Your app is live! 🎉

Here's what you can do now:

#### 1. **Test Your App**
- Visit: `https://your-app-name.herokuapp.com/`
- Try entering some loan data
- Test the calculations
- Download results

#### 2. **Monitor Your App**
```bash
# Check app status
heroku ps

# View logs
heroku logs --tail

# See resource usage
heroku apps:info
```

#### 3. **Push Updates**
If you make changes to your code:

```bash
git add -A
git commit -m "Your changes here"
git push heroku main
```

Your app will redeploy automatically! (Takes 2-5 minutes)

#### 4. **Share Your App**
Your app is now live at: `https://your-app-name.herokuapp.com/`

Share this URL with anyone! They can:
- Use the web interface
- Enter their own loan data
- Download results

#### 5. **View Resource Usage**
```bash
heroku ps
```

You should see something like:
```
Free dyno hours quota remaining this month: 550h
```

The free tier gives you 550 dyno-hours per month (enough to run 24/7 for ~23 days, or part-time indefinitely).

---

## Common Maintenance Tasks

### Restart Your App
```bash
heroku restart
```

### View Recent Logs
```bash
heroku logs -n 50
```

### Check App Info
```bash
heroku apps:info
```

### Delete the App (if needed)
```bash
heroku apps:destroy --app your-app-name
```

---

## Frequently Asked Questions

**Q: How much does this cost?**
A: Heroku's free tier is free! They changed their pricing in late 2022, but your app should still work with the free plan for light usage.

**Q: How fast will my app be?**
A: Free tier Heroku dynos are slower than paid. The MILP optimization might take 30-60 seconds instead of 5-10 seconds locally. This is normal.

**Q: Can people use my app without creating an account?**
A: Yes! Your app is public. Anyone with the URL can use it.

**Q: How do I update my app?**
A: Push code changes to the main branch on GitHub, then:
```bash
git push heroku main
```

**Q: What if the app goes down?**
A: Check logs and restart:
```bash
heroku logs --tail
heroku restart
```

---

## Next Steps

Once your app is deployed and working:

1. ✅ Test all features (manual entry, file upload, all strategies)
2. ✅ Share the URL with friends/colleagues
3. ✅ Monitor the logs for a few days
4. ✅ Consider upgrading to paid tier if you want better performance

---

## Getting Help

If you get stuck:

1. **Check the logs:** `heroku logs --tail`
2. **Read the error message carefully** - it usually tells you what's wrong
3. **Restart the app:** `heroku restart`
4. **Rebuild the app:** `heroku rebuild`

If you're still stuck, you can:
- Check [Heroku documentation](https://devcenter.heroku.com/)
- Search your error message on Google
- Ask me for help! I can guide you through any issues.

---

## Success Checklist

- [ ] Created Heroku account
- [ ] Installed Heroku CLI
- [ ] Logged in with `heroku login`
- [ ] Created app with `heroku create your-app-name`
- [ ] Added buildpacks
- [ ] Committed files to git
- [ ] Pushed to Heroku: `git push heroku main`
- [ ] Visited your live app at https://your-app-name.herokuapp.com/
- [ ] Tested the app (entered loan data, ran calculations)
- [ ] App is working! 🎉

---

**You've got this!** 💪 Let me know if you hit any issues along the way.
