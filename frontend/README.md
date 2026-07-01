# VeriFi Frontend

React chat UI for the VeriFi RAG pipeline. Sends policy questions to the C++ API bridge and displays grounded answers with source citations.

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
| `VITE_API_URL` | `http://localhost:8080` | Base URL for the API bridge |
| `VITE_USE_MOCKS` | `true` | Set to `true` to use MSW mock responses during development |

Set `VITE_USE_MOCKS=false` once the real `API_Connector` backend is running.

## API contract

### `GET /health`

```json
{ "status": "ok" }
```

### `POST /chat`

Request:

```json
{ "message": "What happens if a margin call is issued?" }
```

Response:

```json
{
  "answer": "If a margin call is issued...",
  "sources": [
    {
      "text": "If a margin call is issued, the client must deposit funds within 3 days.",
      "source_document": "Fidelity_Margin_Rules_2026.pdf",
      "page_number": 12,
      "score": 0.94
    }
  ]
}
```

Source citations use the same field names as the `DocumentChunk` struct (`text`, `source_document`, `page_number`), plus a `score` for relevance. Embeddings are not sent to the frontend.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server |
| `npm run build` | Type-check and production build |
| `npm run preview` | Preview production build |
| `npm run lint` | Run oxlint |

## Project structure

```
src/
├── api/           # fetch client, types, endpoint functions
├── components/
│   ├── chat/      # input, messages, empty state
│   ├── citations/ # source cards and list
│   └── layout/    # shell, connection status
├── hooks/         # useChat, useHealth
└── mocks/         # MSW handlers for parallel development
```
