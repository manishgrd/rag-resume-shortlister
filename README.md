# RAG Resume Shortlister (Agentic) – Gemma3:270M + FastAPI + React

This project implements a local, privacy-first resume shortlisting system using:
- **Ollama** running **`gemma3:270m`** as the LLM
- **LangChain** (no LangGraph), **ChromaDB** for vector search
- **FastAPI** backend with SQLite persistence (SQLAlchemy)
- **React (Vite)** frontend for PDF upload and results display
- **Docker Compose** to run everything together

**Key features**
- Upload resume PDFs from the UI.
- Parse, chunk, and embed resumes; store vectors in **Chroma** (on-disk).
- Recruiter-specialized LLM via **Ollama Modelfile** (`recruiter-gemma3:270m`).
- Agentic pipeline: parse → extract facts → RAG → evaluate per requisite → score → summarize.
- REST endpoints to upload, evaluate, and fetch results.
- Results persisted in **SQLite** and queryable via API & shown on the frontend.
- No usage of LangGraph as requested.

## Quick start

```bash
# 1) Build the custom recruiter model and pull base model
make model

# 2) Build & run the full stack
docker compose up --build
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:5173

# (Optional) seed or test upload via curl:
make smoke
```

## Notes
- The backend talks to Ollama at `http://ollama:11434` inside Docker.
- Vector store lives in `backend/storage/chroma/` persisted via a Docker volume.
- SQLite DB persisted via `backend/storage/app.db` (also volume-mounted).
- You can tune rubric weights in `backend/app/scoring.py`.
- Requirements prompts are generated from `backend/app/prompts.py`.
- You can customize the recruiter System Prompt in the `Modelfile`.
```