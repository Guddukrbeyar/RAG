# Enterprise Knowledge Assistant

A full-stack Retrieval-Augmented Generation (RAG) application for asking questions over uploaded enterprise documents. The project uses a React/Vite frontend, a FastAPI backend, local Sentence Transformers embeddings, FAISS vector search, and Ollama for local LLM responses.

## Features

- Login screen with FastAPI-backed credential validation.
- Frontend and backend validation for login, document upload, and chat requests.
- Upload and index PDF, DOCX, TXT, and Markdown files.
- Extract text from uploaded documents and split it into overlapping chunks.
- Generate local embeddings with `sentence-transformers`.
- Store and search document vectors with FAISS.
- Generate grounded answers with a local Ollama model.
- Return source snippets, document names, page numbers where available, and similarity scores.
- Ask for clarification on very short questions.
- Return a clear fallback when no relevant document context is found.

## Tech Stack

- Frontend: React, Vite, lucide-react
- Backend: FastAPI, Pydantic, Uvicorn
- Document parsing: pypdf, python-docx
- Embeddings: Sentence Transformers
- Vector database: FAISS
- LLM runtime: Ollama

## Architecture

```text
React/Vite frontend
   |
   | REST API
   | /api/login
   | /api/documents
   | /api/documents/upload
   | /api/chat
   v
FastAPI backend
   |
   +--> Validate request
   +--> Parse PDF/DOCX/TXT/MD
   +--> Split text into chunks
   +--> Generate local embeddings
   +--> Store/search FAISS index
   +--> Send grounded context to Ollama
   +--> Return answer with sources
```

## Project Structure

```text
.
+-- backend/
|   +-- app/
|   |   +-- main.py       # FastAPI routes
|   |   +-- rag.py        # parsing, chunking, indexing, retrieval, Ollama calls
|   |   +-- schemas.py    # request/response validation models
|   |   +-- config.py     # environment-driven settings
|   +-- requirements.txt
+-- frontend/
|   +-- src/
|   |   +-- main.jsx      # React app
|   |   +-- style.css     # UI styles
|   +-- package.json
+-- data/
    +-- documents/        # uploaded source files
    +-- index/            # FAISS index and metadata
```

The `data/` folders are created automatically by the backend if they do not already exist.

## Prerequisites

- Python 3.10+
- Node.js compatible with the installed Vite version
- Ollama installed and running locally
- An Ollama chat model pulled locally, for example `llama3.2`

Install and start Ollama:

```bash
ollama pull llama3.2
ollama serve
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend runs at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/api/health
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend normally runs at:

```text
http://localhost:5173
```

## Login

Default development credentials:

```text
Username: admin
Password: admin123
```

You can override them with environment variables:

```bash
APP_USERNAME=your_username
APP_PASSWORD=your_password
APP_SESSION_TOKEN=your_session_token
```

## Configuration

Backend settings are defined in `backend/app/config.py` and can be overridden through environment variables.

| Setting | Default | Description |
| --- | --- | --- |
| `APP_USERNAME` | `admin` | Login username |
| `APP_PASSWORD` | `admin123` | Login password |
| `APP_SESSION_TOKEN` | `enterprise-rag-session` | Token returned after login |
| `CHAT_MODEL` | `llama3.2` | Ollama model used for answers |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers embedding model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `TOP_K` | `5` | Number of retrieved chunks |
| `MIN_SIMILARITY` | `0.35` | Retrieval similarity threshold |
| `CHUNK_SIZE` | `900` | Maximum chunk size |
| `CHUNK_OVERLAP` | `150` | Chunk overlap size |
| `DATA_DIR` | `../data` | Data directory relative to the project root |

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Backend health check |
| `POST` | `/api/login` | Validate login credentials |
| `GET` | `/api/documents` | List uploaded documents |
| `POST` | `/api/documents/upload` | Upload and index a document |
| `POST` | `/api/chat` | Ask a question over indexed documents |

## How It Works

1. Sign in from the frontend.
2. Upload a supported document.
3. The backend extracts document text.
4. Text is split into overlapping chunks.
5. Chunks are embedded locally with Sentence Transformers.
6. FAISS stores the vectors and metadata.
7. A chat question is embedded and searched against the FAISS index.
8. Relevant chunks are sent to Ollama as grounded context.
9. The answer is returned with supporting source snippets.

## Validation

The app validates:

- Login username and password presence.
- Chat question presence and maximum length.
- Upload file extension: `.pdf`, `.docx`, `.txt`, `.md`.
- Empty uploaded files.
- Backend request bodies with Pydantic schemas.

## Notes

- The app is designed for local development and demo use.
- The login token is stored in browser local storage and is not used as full production authentication.
- Uploaded documents are saved in `data/documents/`.
- FAISS index files and metadata are saved in `data/index/`.
- If no matching context is found, the assistant responds with: `I couldn't find this in the available documents.`
