# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

### Running with Docker

Requires Docker with Compose. You still need a `.env` file at the project root
containing `ANTHROPIC_API_KEY`.

```bash
docker compose up --build
```

The app is served at `http://localhost:8000`. Notes:

- On first startup the container downloads the `all-MiniLM-L6-v2` embedding model
  from HuggingFace (~90 MB). It is cached in the `hf_cache` volume, so subsequent
  starts are offline and fast.
- The ChromaDB vector store is persisted in the `chroma_data` volume.
- `./docs` is mounted into the container; any `.txt`/`.pdf`/`.docx` course files
  placed there are ingested on the next startup.

To run the image directly without Compose:

```bash
docker build -t course-rag .
docker run --rm -p 8000:8000 --env-file .env \
  -v course-rag-chroma:/app/backend/chroma_db \
  -v course-rag-hf:/app/.cache/huggingface \
  course-rag
```

