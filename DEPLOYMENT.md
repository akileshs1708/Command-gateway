# 🚀 Deploying Command Gateway to Render

This guide covers deploying both the **Backend (FastAPI)** and **Frontend (Static)** to Render.

---

## 📋 Prerequisites

1. A [Render account](https://render.com) (free tier works!)
2. Your code pushed to a **GitHub** or **GitLab** repository
3. Repository should have this structure:
   ```
   command-gateway/
   ├── backend/
   │   ├── main.py
   │   ├── database.py
   │   ├── models.py
   │   ├── auth.py
   │   ├── rules.py
   │   └── commands.py
   ├── frontend/
   │   ├── index.html
   │   ├── styles.css
   │   └── script.js
   ├── requirements.txt
   ├── render.yaml
   └── Procfile
   ```

---

## 🔧 Method 1: Blueprint Deployment (Recommended)

The easiest way using `render.yaml`:

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/command-gateway.git
git push -u origin main
```

### Step 2: Deploy with Blueprint

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will detect `render.yaml` and create both services
5. Click **"Apply"**

### Step 3: Get Your URLs

After deployment:
- **Backend API**: `https://command-gateway-api.onrender.com`
- **Frontend**: `https://command-gateway-frontend.onrender.com`

### Step 4: Update Frontend API URL

1. Go to your frontend service in Render
2. The `script.js` auto-detects the backend URL, but if you need to set it manually:
   - Add environment variable or update the code

---

## 🔧 Method 2: Manual Deployment (Step by Step)

### Part A: Deploy Backend (Web Service)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New"** → **"Web Service"**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `command-gateway-api`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

5. Add **Environment Variables**:
   | Key | Value |
   |-----|-------|
   | `PYTHON_VERSION` | `3.11` |
   | `DATABASE_PATH` | `/tmp/command_gateway.db` |
   | `ADMIN_API_KEY` | `your-secure-admin-key` |
   | `ALLOWED_ORIGINS` | `*` (or your frontend URL) |

6. Click **"Create Web Service"**

7. **Copy the URL** (e.g., `https://command-gateway-api.onrender.com`)

### Part B: Deploy Frontend (Static Site)

1. Go to Render Dashboard
2. Click **"New"** → **"Static Site"**
3. Connect the same GitHub repo
4. Configure:
   - **Name**: `command-gateway-frontend`
   - **Branch**: `main`
   - **Build Command**: (leave empty or `echo "No build"`)
   - **Publish Directory**: `frontend`

5. Click **"Create Static Site"**

### Part C: Connect Frontend to Backend

**Option 1: The script auto-detects** (already implemented)

The `script.js` uses:
```javascript
const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : window.location.origin;
```

**Option 2: If using separate domains**, update `frontend/script.js`:

```javascript
const API_BASE_URL = 'https://command-gateway-api.onrender.com';
```

Then redeploy the frontend.

---

## 🔧 Method 3: Single Combined Deployment

Deploy both backend and frontend as one service:

1. The `main.py` already serves frontend files if they exist
2. Create a single Web Service with:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
3. The root URL `/` will serve the frontend
4. API endpoints work at `/commands`, `/rules`, etc.

---

## ⚙️ Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port (auto-set by Render) | `8000` |
| `DATABASE_PATH` | SQLite database path | `./command_gateway.db` |
| `ADMIN_API_KEY` | Default admin API key | `admin-key-12345` |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `*` |

---

## 📝 Important Notes

### Database Persistence

⚠️ **Render's free tier uses ephemeral storage!**

The SQLite database at `/tmp/command_gateway.db` will be **reset on each deploy**.

**Solutions:**

1. **Render Disk** (paid): Add a persistent disk
   ```yaml
   disk:
     name: command-gateway-data
     mountPath: /data
     sizeGB: 1
   ```
   Then set `DATABASE_PATH=/data/command_gateway.db`

2. **External Database**: Use PostgreSQL
   - Add Render PostgreSQL service
   - Update `database.py` to use PostgreSQL connection string

3. **Accept ephemeral**: For demos/testing, the default admin and rules are re-seeded on each restart

### Free Tier Limitations

- Services **spin down after 15 minutes** of inactivity
- First request after spin-down takes **~30 seconds** (cold start)
- Storage is ephemeral

### Custom Domain

1. Go to your service → **Settings** → **Custom Domain**
2. Add your domain
3. Update DNS with provided CNAME record

---

## 🔍 Verification Steps

### 1. Check Backend Health

```bash
curl https://command-gateway-api.onrender.com/health
```

Expected response:
```json
{"status": "healthy", "service": "command-gateway"}
```

### 2. Check API Docs

Visit: `https://command-gateway-api.onrender.com/docs`

### 3. Test Login

Open frontend and login with:
- **API Key**: `admin-key-12345` (or your custom `ADMIN_API_KEY`)

### 4. Submit Test Command

Try `ls -la` (should execute) and `rm -rf /` (should reject)

---

## 🐛 Troubleshooting

### "Cannot connect to server"

1. Check if backend is deployed and running
2. Check browser console for CORS errors
3. Verify `API_BASE_URL` in `script.js`

### "Invalid API key"

1. Check `ADMIN_API_KEY` environment variable
2. Database may have reset - use the key from env vars

### CORS Errors

1. Set `ALLOWED_ORIGINS` to your frontend URL:
   ```
   ALLOWED_ORIGINS=https://command-gateway-frontend.onrender.com
   ```

### Slow First Load

- Normal for free tier (cold start)
- Upgrade to paid tier for always-on

---

## 📊 Architecture on Render

```
┌─────────────────────────────────────────────────────────────┐
│                         RENDER                               │
│                                                              │
│  ┌─────────────────────┐      ┌─────────────────────────┐  │
│  │   Static Site       │      │      Web Service        │  │
│  │   (Frontend)        │      │      (Backend)          │  │
│  │                     │      │                         │  │
│  │  - index.html       │ HTTP │  - FastAPI              │  │
│  │  - styles.css       │─────▶│  - SQLite               │  │
│  │  - script.js        │      │  - Python 3.11          │  │
│  │                     │      │                         │  │
│  │  URL: *.onrender.com│      │  URL: *.onrender.com    │  │
│  └─────────────────────┘      └─────────────────────────┘  │
│                                          │                   │
│                                          ▼                   │
│                               ┌─────────────────────┐       │
│                               │  /tmp/database.db   │       │
│                               │  (ephemeral)        │       │
│                               └─────────────────────┘       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] `requirements.txt` includes all dependencies
- [ ] `render.yaml` or manual configuration done
- [ ] Backend deployed and `/health` returns OK
- [ ] Frontend deployed and loads correctly
- [ ] `ADMIN_API_KEY` set (save it!)
- [ ] Login works with admin key
- [ ] Commands execute/reject correctly
- [ ] (Optional) Custom domain configured

---

## 🎉 Done!

Your Command Gateway is now live on Render!

**URLs:**
- Frontend: `https://your-frontend.onrender.com`
- Backend: `https://your-backend.onrender.com`
- API Docs: `https://your-backend.onrender.com/docs`
