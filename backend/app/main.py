from pathlib import Path

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    ChatRequest,
    ChatResponse,
    DocumentInfo,
    LoginRequest,
    LoginResponse
)

from .config import get_settings

from .rag import (
    DOCS,
    rebuild_index,
    answer
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Enterprise Knowledge Assistant",
    version="2.0.0"
)

settings = get_settings()


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "ai": "local",
        "llm": "ollama"
    }


# ============================================================
# LOGIN
# ============================================================

@app.post(
    "/api/login",
    response_model=LoginResponse
)
def login(req: LoginRequest):

    if (
        req.username != settings.app_username
        or req.password != settings.app_password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password."
        )

    return {
        "token": settings.app_session_token,
        "username": req.username
    }


# ============================================================
# DOCUMENTS
# ============================================================

@app.get(
    "/api/documents",
    response_model=list[DocumentInfo]
)
def documents():

    result = []

    for path in sorted(DOCS.iterdir()):

        if not path.is_file():
            continue

        result.append(
            {
                "name": path.name,
                "chunks": 0
            }
        )

    return result


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@app.post("/api/documents/upload")
async def upload(
    file: UploadFile = File(...)
):

    allowed = {
        ".pdf",
        ".docx",
        ".txt",
        ".md"
    }

    filename = file.filename or ""

    ext = Path(filename).suffix.lower()

    if ext not in allowed:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Supported: PDF, DOCX, TXT, MD"
            )
        )

    # Prevent directory traversal
    safe_name = Path(filename).name

    if not safe_name:

        raise HTTPException(
            status_code=400,
            detail="Invalid filename."
        )

    target = DOCS / safe_name

    try:

        content = await file.read()

        if not content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        target.write_bytes(content)

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save document: {exc}"
        )

    # --------------------------------------------------------
    # Rebuild vector index
    # --------------------------------------------------------

    try:

        chunks = rebuild_index()

    except Exception as exc:

        # Remove broken document if indexing failed
        if target.exists():
            target.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to index document: {exc}"
        )

    return {
        "message":
            "Document indexed successfully",
        "document":
            target.name,
        "chunks":
            chunks
    }


# ============================================================
# CHAT
# ============================================================

@app.post(
    "/api/chat",
    response_model=ChatResponse
)
def chat(req: ChatRequest):

    try:

        return answer(
            req.question
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
