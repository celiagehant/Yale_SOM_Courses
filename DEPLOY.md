# Deploying to Render

Two services: a **Web Service** for the FastAPI backend and a **Static Site**
for the React frontend.

There are two ways to do it. The Blueprint route fills in every field for you;
the manual route is what to type if you create the two services by hand.

---

## Option A — Blueprint (fills everything in)

1. In Render: **New +** → **Blueprint**
2. Pick the `Yale_SOM_Courses` repo
3. Render reads [`render.yaml`](render.yaml) and proposes both services
4. It will prompt for **`PORTKEY_API_KEY`** — paste your Portkey key
5. **Apply**

That's it. The frontend's `VITE_API_BASE` is wired to the backend's hostname
automatically, so you don't have to copy any URLs between services.

---

## Option B — creating the two services by hand

### 1. Web Service (backend)

| Field | Value |
| --- | --- |
| Type | Web Service |
| Repository | `celiagehant/Yale_SOM_Courses` |
| Branch | `main` |
| **Root Directory** | `backend` |
| Language / Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/health` |
| Instance Type | Free |

**Environment variable:**

| Key | Value |
| --- | --- |
| `PORTKEY_API_KEY` | your real Portkey key |

Python version comes from `backend/.python-version` (3.13.4).

Deploy this one **first** — you need its URL for the frontend. It'll look like
`https://yale-som-courses-api.onrender.com`. Check it works:

```bash
curl https://yale-som-courses-api.onrender.com/api/health
```

### 2. Static Site (frontend)

| Field | Value |
| --- | --- |
| Type | Static Site |
| Repository | `celiagehant/Yale_SOM_Courses` |
| Branch | `main` |
| **Root Directory** | `frontend` |
| Build Command | `npm ci && npm run build` |
| **Publish Directory** | `dist` |

**Environment variable:**

| Key | Value |
| --- | --- |
| `VITE_API_BASE` | the backend URL from step 1, e.g. `https://yale-som-courses-api.onrender.com` |

**Redirect/Rewrite rule** (Redirects/Rewrites tab):

| Source | Destination | Action |
| --- | --- | --- |
| `/*` | `/index.html` | Rewrite |

---

## Things that will trip you up

- **`VITE_API_BASE` is baked in at build time.** Vite inlines it into the
  bundle, so changing it in the dashboard does nothing until you trigger a new
  deploy. Change the value, then **Manual Deploy → Deploy latest commit**.
- **Free services sleep after ~15 minutes idle.** The first request afterwards
  takes 30–60 seconds while the backend wakes up. The chat panel will just look
  slow. If the catalog fails to load on first visit, reload once.
- **Deploy the backend before the static site** if you're doing it manually —
  otherwise you have no URL to paste.
- **The audit trail does not persist.** `output/audit_trail.json` is written to
  Render's ephemeral disk, so it resets on every deploy and every restart. Your
  local copy is the one that accumulates history. If you need it to survive in
  production, that needs a database or a Render disk.
- **CORS is wide open** (`allow_origins=["*"]` in `main.py`). Fine for a class
  project; if you want to lock it to your static site's origin later, that's
  the line to change.
- **The key must never go in the repo.** `.env` is gitignored. On Render it
  lives in the dashboard's environment variables only.
