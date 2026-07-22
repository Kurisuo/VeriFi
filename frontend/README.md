# VeriFi Frontend

React chat UI for the VeriFi RAG pipeline. Landing page → chat handoff, grounded
answers with source citations, and optional MSW mocks for offline / Pages demos.

**Live site:** [https://kurisuo.github.io/VeriFi/](https://kurisuo.github.io/VeriFi/)

## Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The app runs at `http://localhost:5173` by default.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `/api` | Base URL for API calls. `/api` uses the Vite dev proxy (no CORS needed). Use `http://localhost:8000` for direct calls once CORS is configured. |
| `VITE_USE_MOCKS` | `true` | Set to `true` for MSW mock responses; `false` to hit the real FastAPI backend. |

### Connecting to the real backend

1. Start the FastAPI server (from `backend/`):
   ```bash
   cd backend
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   uvicorn --app-dir src main:app --reload --port 8000
   ```
2. Set `VITE_USE_MOCKS=false` in `.env`
3. Keep `VITE_API_URL=/api` — the Vite proxy forwards `/api/*` to `localhost:8000` without requiring CORS changes

## GitHub Pages

Pushes to `main` run [`.github/workflows/deploy-pages.yml`](../.github/workflows/deploy-pages.yml),
which builds **this** `frontend/` directory and deploys `frontend/dist`.

CI build env (set in the workflow — do not rely on a local `.env` for Pages):

| Variable | CI value | Why |
|----------|----------|-----|
| `GITHUB_PAGES` | `true` | Sets Vite `base` to `/VeriFi/` and copies `index.html` → `404.html` for SPA routes |
| `VITE_USE_MOCKS` | `true` | Pages is static; no FastAPI host |
| `VITE_API_URL` | `/api` | Matches the mock worker / client base URL |

After merge, confirm the latest commit appears under **Actions → Deploy frontend
to GitHub Pages**, then hard-refresh the live URL (Pages can cache for a few
minutes). Manual redeploy: **Actions → Run workflow**.

**SPA routing note:** Internal nav must use React Router `Link` / `navigate`
(or `import.meta.env.BASE_URL`), not root-absolute `<a href="/chat">`. Those
resolve to `kurisuo.github.io/chat` and 404 outside the `/VeriFi/` base.

## API contract (FastAPI — `backend/src/main.py`)

### `GET /health`

```json
{ "status": "ok" }
```

### `POST /chat`

Request:

```json
{ "query": "What happens if a margin call is issued?" }
```

Response:

```json
{
  "answer": "If a margin call is issued...",
  "sources": [
    {
      "doc": "terms-and-conditions.pdf",
      "page": 12,
      "snippet": "If a margin call is issued, the client must deposit funds within 3 days.",
      "score": 0.94
    }
  ]
}
```

The frontend normalizes backend fields (`doc`, `page`, `snippet`) to internal UI types (`source_document`, `page_number`, `text`) in `src/api/normalize.ts`.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server with API proxy |
| `npm run build` | Type-check and production build |
| `npm run preview` | Preview production build |
| `npm run lint` | Run oxlint |

## Project structure

```
src/
├── api/           # fetch client, types, normalize layer, endpoint functions
├── components/
│   ├── chat/      # input, messages, empty state
│   ├── citations/ # source cards and list
│   └── layout/    # shell, sidebars, connection status
├── hooks/         # useChat, useHealth
├── pages/         # LandingPage, ChatPage
└── mocks/         # MSW handlers (return FastAPI wire format)
```
