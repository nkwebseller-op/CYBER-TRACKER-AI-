# Railway Deployment Guide - Cyber AI Backend

## Quick Start

Your Cyber AI backend is ready to deploy to Railway. Follow these steps:

### Step 1: Go to Railway Dashboard
1. Open https://railway.app/dashboard
2. Sign in with your account (already connected)
3. Create a new project or select existing

### Step 2: Create PostgreSQL Database
1. Click "Add Service" → "Database"
2. Select "PostgreSQL"
3. Railway will auto-generate a `DATABASE_URL`
4. **Save this URL** - you'll need it in Step 4

### Step 3: Create FastAPI Service
1. Click "Add Service" → "GitHub Repo"
2. Select this repository: `nkwebseller-op/CYBER-TRACKER-AI-`
3. Branch: `claude/cyber-ai-foundation-upar86`
4. Root Directory: `apps/api`
5. Keep "Dockerfile" auto-detection enabled

### Step 4: Configure Environment Variables
In Railway service settings, add these variables:

```
ENVIRONMENT=production
API_SECRET_KEY=[Generate a random 32+ character string]
API_CORS_ORIGINS=https://cyber-ai-system.vercel.app
AI_PROVIDER=gemini
GEMINI_API_KEY=[Your Gemini API key from https://aistudio.google.com/apikey]
DATABASE_URL=[Copy from PostgreSQL service - see Step 2]
```

**To generate API_SECRET_KEY**, run this and paste the output:
```bash
openssl rand -base64 32
```

Or use any 32+ character random string.

### Step 5: Deploy
1. Railway will auto-deploy when you add the service
2. Wait for green checkmark on both PostgreSQL and FastAPI services
3. Click the FastAPI service
4. Go to "Settings" → "Environment" → find the generated public domain
5. **Copy the public URL** (looks like: `https://cyber-ai-backend-production-xxx.up.railway.app`)

### Step 6: Update Frontend
Once you have the Railway backend URL, run:

```bash
cd apps/web
# Set the environment variable
export NEXT_PUBLIC_API_BASE_URL="https://your-railway-backend-url"
npm run build
```

Then redeploy to Vercel, or the auto-deploy on next push to branch will use it.

---

## What's Being Deployed

- **Frontend**: ✅ Already deployed to https://cyber-ai-system.vercel.app
- **Android APK**: ✅ Available in GitHub Releases
- **Backend API**: 🚀 Deploying now to Railway
  - FastAPI with WebSocket support
  - Gemini AI integration
  - PostgreSQL database
  - Termux connector gateway

---

## Backend Endpoints

Once deployed, your backend will provide:

- `POST /api/chat` - Send messages to AI
- `GET /api/targets` - Cybersecurity targets
- `POST /api/targets` - Create authorization targets
- `WebSocket /ws` - Real-time communication
- `WebSocket /ws/termux` - Termux device pairing

---

## Next Steps After Deployment

1. ✅ Verify backend is running (check Railway dashboard)
2. Update `NEXT_PUBLIC_API_BASE_URL` in frontend
3. Test the chat feature end-to-end
4. Configure Termux connector with backend URL
5. Test Termux device pairing

---

## Troubleshooting

**Build fails**: Ensure `apps/api/requirements.txt` is accessible and all dependencies are compatible.

**Database connection fails**: Double-check `DATABASE_URL` format and that PostgreSQL service is running.

**CORS errors**: Verify `API_CORS_ORIGINS` includes your frontend URL without typos.

**Gemini API errors**: Check the API key is valid and has quota available at https://aistudio.google.com/apikey

---

## Files Prepared for Railway

- `apps/api/railway.json` - Railway configuration
- `apps/api/.env.production.example` - Environment template
- `apps/api/Dockerfile` - Container definition (already present)
- `apps/api/requirements.txt` - Python dependencies
