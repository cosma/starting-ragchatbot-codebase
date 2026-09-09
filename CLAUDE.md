# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Retrieval-Augmented Generation (RAG) system that answers questions about course materials. FastAPI backend + vanilla JS frontend, ChromaDB for vector storage, Anthropic Claude for generation via tool calling.

## Commands

Install dependencies (uses `uv`, not pip/poetry directly):
```bash
uv sync
```

Set the required API key in a `.env` file at the project root:
```bash
ANTHROPIC_API_KEY=your_key_here
```

Run the app (auto-reload dev server):
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

- Web UI: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

There is no test suite, linter, or build step configured in this repo currently.

Run in a container (needs `.env` with `ANTHROPIC_API_KEY` at the project root):
```bash
docker compose up --build
```
`Dockerfile` is a single-stage `uv` build (single-stage on purpose — the target Docker VM has only 2 GiB RAM and a multi-stage venv copy OOM-crashed it). The container runs `uvicorn` from `/app/backend` (no `--reload`). The embedding model downloads on first start into the `hf_cache` volume; ChromaDB persists in `chroma_data`; `./docs` is bind-mounted for ingestion.

## Development conventions

- Always use `uv` for dependency management and for running any Python code (`uv sync`, `uv add`, `uv run python ...`, `uv run uvicorn ...`) — never call `pip` or bare `python`/`python3` directly.
- Use descriptive variable names; avoid abbreviations or terse identifiers.

## Architecture

Request flow: `frontend/script.js` → `POST /api/query` (`backend/app.py`) → `RAGSystem.query()` (`backend/rag_system.py`) → `AIGenerator` (`backend/ai_generator.py`) → Claude, with tool calling into `CourseSearchTool` (`backend/search_tools.py`) → `VectorStore` (`backend/vector_store.py`) → ChromaDB.

**Tool-calling is capped at one round.** `AIGenerator._handle_tool_execution()` makes exactly one follow-up API call after a `tool_use` response, with `tools` omitted from that second call. Claude cannot chain a second search within the same turn — this is enforced both structurally (no tools available on the follow-up call) and via the system prompt ("One search per query maximum"). Keep this in mind when changing search/tool logic — it's a deliberate constraint, not an oversight.

**ChromaDB uses two separate collections** (`backend/vector_store.py`):
- `course_catalog` — one row per course, embeds the course title for fuzzy name resolution (`_resolve_course_name`). Lesson lists are serialized to a `lessons_json` string field since Chroma metadata must be flat scalars.
- `course_content` — one row per chunk, the actual searchable material, filterable by `course_title` / `lesson_number`.

A course's `title` is its identity across the whole system: it's the Chroma document ID in `course_catalog`, the `course_title` foreign key on every chunk in `course_content`, and how `RAGSystem.add_course_folder` deduplicates already-ingested courses on startup/reload.

**Document ingestion** (`backend/document_processor.py`) expects a specific plain-text format:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<lesson body text>

Lesson 1: <title>
...
```
Lessons are split out via `Lesson N: ...` markers, then each lesson's text is sentence-chunked (`chunk_text`) with configurable size/overlap and sentence-boundary awareness (avoids breaking on abbreviations). The first chunk of a lesson is prefixed with `"Lesson {N} content: ..."` and the last lesson's chunks get `"Course {title} Lesson {N} content: ..."` — this context-prefixing is intentional so embedded chunks retain course/lesson identity even in isolation.

On server startup (`app.py` `startup_event`), `docs/` is scanned and any `.pdf`/`.docx`/`.txt` files whose parsed course title isn't already in `course_catalog` get ingested automatically — existing courses are skipped, not re-processed.

**Session/conversation state** (`backend/session_manager.py`) is in-memory only (a plain dict keyed by session ID, not persisted), capped at `MAX_HISTORY * 2` messages (user+assistant pairs).

**Config is centralized** in `backend/config.py` (a single dataclass instance `config`): chunk size/overlap, embedding model name, Anthropic model name, max search results, max history length, ChromaDB path. Change tuning parameters there rather than inline.

**Frontend is unbuilt** — `frontend/` is served directly as static files by FastAPI (mounted at `/` via `StaticFiles`, `app.py`), no bundler/framework. Cache-busting for dev is handled with explicit `Cache-Control: no-cache` headers on the static file handler and a `?v=N` query string on the CSS link in `index.html` — bump that version string when editing `style.css` if changes aren't showing up.
