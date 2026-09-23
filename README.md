# Yale SOM Course Explorer

A full-stack course explorer for the Yale School of Management catalog: a React
catalog of courses plus a chat agent that answers questions using tools over
`data/yale_som_classes.json`, falling back to web search when the catalog isn't
enough.

- **Backend** — FastAPI + [pydantic-ai](https://ai.pydantic.dev), model
  `gpt-6-astra` reached through Portkey
- **Frontend** — React + TypeScript + Vite

## Setup

The agent needs a Portkey API key. Copy the example file and fill it in:

```bash
cp .env.example .env
```

`.env` is gitignored — never commit the real key. The backend also looks one
directory up, so a shared `.env` in the parent folder works too.

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173

Both servers need to be running — the chat panel calls the backend on port 8000.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness check |
| `GET /api/courses?q=` | Course catalog, with an optional text filter |
| `POST /api/chat` | `{"message": "..."}` → `{"reply", "tools_used"}` |

## How the agent works

`backend/agent.py` builds a pydantic-ai agent with exactly two tools:

1. **`search_courses`** (`backend/tools.py`) — searches the catalog JSON by
   title, number, faculty, subject area, course type, and weekday. Results are
   capped at 15.
2. **`web_search`** — OpenAI's native provider-side web search, for faculty
   news and context the catalog doesn't carry.

The system prompt lives in `backend/prompts/prompt.md`. Every run is appended
to `output/audit_trail.json` with the user message, each tool call and its
arguments, a truncated result, and why the loop stopped.

### Two quirks in the catalog data

Both of these caused wrong answers before they were handled, and are worth
knowing if you extend the search tool:

- **`Elective` is not a Course Category.** Categories are subject areas
  (Finance, Marketing, Operations…); `core` / `elective` / `PhD` live in
  `Course Type`. The `category` filter checks both fields.
- **`Timings Day` is blank on 209 of 234 rows.** Most courses encode their
  meeting days only inside the `Daytimes` string (`"T  Th 1:00 PM-2:20 PM"`),
  so `Course.day_codes()` parses that as a fallback.

## Layout

```
.
├── data/yale_som_classes.json   course catalog (234 records)
├── backend/
│   ├── main.py                  FastAPI app
│   ├── agent.py                 pydantic-ai agent + audit trail
│   ├── tools.py                 search_courses + native web search
│   ├── models.py                Course, AgentResult, AuditEntry, …
│   └── prompts/prompt.md        system prompt
├── frontend/src/
│   ├── App.tsx                  catalog + layout
│   ├── api.ts                   typed backend client
│   └── components/              CourseCard, CourseGrid, ChatPanel
└── output/audit_trail.json      one appended entry per agent run
```
