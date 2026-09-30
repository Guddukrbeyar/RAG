import json
import re
import requests
from pathlib import Path
from typing import List, Dict

import faiss
import numpy as np
import requests
from docx import Document
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from .config import get_settings


settings = get_settings()


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE = Path(__file__).resolve().parents[2]

DATA = (BASE / settings.data_dir).resolve()

DOCS = DATA / "documents"
INDEX_DIR = DATA / "index"

DOCS.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

META_FILE = INDEX_DIR / "metadata.json"
INDEX_FILE = INDEX_DIR / "faiss.index"


# ============================================================
# LOCAL EMBEDDING MODEL
# ============================================================

print(
    f"Loading embedding model: "
    f"{settings.embedding_model}"
)

embedding_model = SentenceTransformer(
    settings.embedding_model
)

print("Embedding model loaded.")


# ============================================================
# DOCUMENT EXTRACTION
# ============================================================

def extract_text(path: Path):
    """
    Extract text from supported document types.

    Returns:
        List[Tuple[page_number, text]]
    """

    ext = path.suffix.lower()

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if ext == ".pdf":

        reader = PdfReader(str(path))

        pages = []

        for i, page in enumerate(reader.pages):

            text = page.extract_text() or ""

            pages.append(
                (i + 1, text)
            )

        return pages

    # --------------------------------------------------------
    # DOCX
    # --------------------------------------------------------

    if ext == ".docx":

        doc = Document(str(path))

        text = "\n".join(
            paragraph.text
            for paragraph in doc.paragraphs
            if paragraph.text.strip()
        )

        return [
            (None, text)
        ]

    # --------------------------------------------------------
    # TXT / MARKDOWN
    # --------------------------------------------------------

    if ext in {".txt", ".md"}:

        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        return [
            (None, text)
        ]

    raise ValueError(
        "Supported files: PDF, DOCX, TXT, MD"
    )


# ============================================================
# TEXT CHUNKING
# ============================================================

def split_chunks(
    text: str,
    size: int,
    overlap: int
):
    """
    Split text into overlapping chunks.
    """

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + size,
            len(text)
        )

        # Try to end at a sentence boundary.
        if end < len(text):

            boundary = max(
                text.rfind(". ", start, end),
                text.rfind("; ", start, end),
                text.rfind(", ", start, end)
            )

            if boundary > start + size // 2:

                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(
            end - overlap,
            start + 1
        )

    return chunks


# ============================================================
# EMBEDDINGS
# ============================================================

def create_embeddings(texts: List[str]):
    """
    Generate local embeddings using Sentence Transformers.
    """

    if not texts:
        return np.empty(
            (0, 384),
            dtype="float32"
        )

    vectors = embedding_model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    return vectors.astype("float32")


# ============================================================
# BUILD FAISS INDEX
# ============================================================

def rebuild_index():

    metadata: List[Dict] = []

    texts = []

    # --------------------------------------------------------
    # Read documents
    # --------------------------------------------------------

    for path in sorted(DOCS.iterdir()):

        if path.suffix.lower() not in {
            ".pdf",
            ".docx",
            ".txt",
            ".md"
        }:
            continue

        try:

            pages = extract_text(path)

        except Exception as exc:

            print(
                f"Failed to read {path.name}: {exc}"
            )

            continue

        for page, text in pages:

            chunks = split_chunks(
                text,
                settings.chunk_size,
                settings.chunk_overlap
            )

            for idx, chunk in enumerate(chunks):

                metadata.append(
                    {
                        "document": path.name,
                        "page": page,
                        "chunk": idx,
                        "text": chunk
                    }
                )

                texts.append(chunk)

    # --------------------------------------------------------
    # No documents
    # --------------------------------------------------------

    if not texts:

        if INDEX_FILE.exists():
            INDEX_FILE.unlink()

        META_FILE.write_text(
            "[]",
            encoding="utf-8"
        )

        return 0

    # --------------------------------------------------------
    # Generate local embeddings
    # --------------------------------------------------------

    print(
        f"Generating embeddings for "
        f"{len(texts)} chunks..."
    )

    matrix = create_embeddings(texts)

    # --------------------------------------------------------
    # Create FAISS index
    # --------------------------------------------------------

    dimension = matrix.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(matrix)

    faiss.write_index(
        index,
        str(INDEX_FILE)
    )

    # --------------------------------------------------------
    # Save metadata
    # --------------------------------------------------------

    META_FILE.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"FAISS index created with "
        f"{len(metadata)} chunks."
    )

    return len(metadata)


# ============================================================
# VECTOR SEARCH
# ============================================================

def search(question: str):

    if (
        not INDEX_FILE.exists()
        or not META_FILE.exists()
    ):
        return []

    # --------------------------------------------------------
    # Embed question locally
    # --------------------------------------------------------

    query_vector = create_embeddings(
        [question]
    )

    # --------------------------------------------------------
    # Load FAISS
    # --------------------------------------------------------

    index = faiss.read_index(
        str(INDEX_FILE)
    )

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    scores, ids = index.search(
        query_vector,
        settings.top_k
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata = json.loads(
        META_FILE.read_text(
            encoding="utf-8"
        )
    )

    results = []

    for score, idx in zip(
        scores[0],
        ids[0]
    ):

        if idx < 0:
            continue

        if idx >= len(metadata):
            continue

        score = float(score)

        if score < settings.min_similarity:
            continue

        item = metadata[idx].copy()

        item["score"] = score

        results.append(item)

    return results


# ============================================================
# OLLAMA
# ============================================================

def call_ollama(
    system_prompt: str,
    user_prompt: str
) -> str:

    url = (
        f"{settings.ollama_base_url}"
        "/api/chat"
    )

    payload = {
        "model": settings.chat_model,

        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],

        "stream": False,

        "options": {
            "temperature": 0
        }
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=300
        )

        response.raise_for_status()

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "Cannot connect to Ollama. "
            "Make sure Ollama is running with "
            "'ollama serve'."
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "Ollama request timed out."
        )

    except requests.exceptions.HTTPError as exc:

        raise RuntimeError(
            f"Ollama error: {exc} - "
            f"{response.text}"
        )

    data = response.json()

    message = data.get(
        "message",
        {}
    )

    content = message.get(
        "content",
        ""
    )

    if not content:

        raise RuntimeError(
            "Ollama returned an empty response."
        )

    return content.strip()


# ============================================================
# ANSWER QUESTION
# ============================================================

def answer(question: str):

    question = question.strip()

    # --------------------------------------------------------
    # Empty question
    # --------------------------------------------------------

    if not question:

        return {
            "answer": "Please type a question.",
            "grounded": False,
            "sources": [],
            "clarification": None
        }

    # --------------------------------------------------------
    # Very short question
    # --------------------------------------------------------

    if len(question.split()) <= 1:

        return {
            "answer": "",
            "grounded": False,
            "sources": [],
            "clarification":
                "Could you clarify what you want to know?"
        }

    # --------------------------------------------------------
    # Semantic search
    # --------------------------------------------------------

    hits = search(question)

    # --------------------------------------------------------
    # Nothing relevant
    # --------------------------------------------------------

    if not hits:

        return {
            "answer":
                "I couldn't find this in the available documents.",
            "grounded": False,
            "sources": [],
            "clarification": None
        }

    # --------------------------------------------------------
    # Build context
    # --------------------------------------------------------

    context_parts = []

    for i, hit in enumerate(hits):

        page = hit.get("page")

        page_text = (
            f"page {page}"
            if page is not None
            else "document"
        )

        context_parts.append(
            f"[{i + 1}] "
            f"{hit['document']} "
            f"{page_text}: "
            f"{hit['text']}"
        )

    context = "\n\n".join(
        context_parts
    )

    # --------------------------------------------------------
    # System prompt
    # --------------------------------------------------------

    system_prompt = """
You are an enterprise knowledge assistant.

Your job is to answer questions ONLY using
the supplied document context.

Rules:

1. Do not use outside knowledge.
2. Do not invent facts.
3. If the context does not contain enough
   information, clearly say:
   "I couldn't find this in the available documents."
4. Cite factual claims using [1], [2], etc.
5. Keep the answer concise and factual.
6. Prefer information directly supported
   by the provided context.
7. If multiple sources support an answer,
   cite all relevant sources.
"""

    # --------------------------------------------------------
    # User prompt
    # --------------------------------------------------------

    user_prompt = f"""
Context:

{context}


Question:

{question}


Answer using ONLY the context above.
"""

    # --------------------------------------------------------
    # Generate answer
    # --------------------------------------------------------

    generated_answer = call_ollama(
        system_prompt,
        user_prompt
    )

    # --------------------------------------------------------
    # Sources
    # --------------------------------------------------------

    sources = []

    for hit in hits:

        sources.append(
            {
                "document": hit["document"],
                "page": hit.get("page"),
                "section": None,
                "snippet": hit["text"],
                "score": hit["score"]
            }
        )

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    return {
        "answer": generated_answer,
        "grounded": True,
        "sources": sources,
        "clarification": None
    }