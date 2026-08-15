import os
import uuid
import fitz  # pymupdf
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
chroma_client = chromadb.PersistentClient(path="./chroma_store")

COLLECTION_NAME = "company_knowledge"
EMBED_MODEL = "openai/text-embedding-3-small"   # OpenRouter model naming
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# ... rest of the file stays exactly the same


def extract_text_from_pdf(pdf_path: str) -> str:
    """Pull all text out of a PDF, page by page."""
    doc = fitz.open(pdf_path)
    full_text = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            full_text.append(f"[Page {page_num}]\n{text}")
    doc.close()
    return "\n\n".join(full_text)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Simple sliding-window chunker. Good enough for a hackathon RAG layer."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed a list of text chunks via OpenAI."""
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in response.data]


def ingest_pdf(pdf_path: str, source_label: str = None) -> int:
    """
    Full ingestion pipeline: PDF -> text -> chunks -> embeddings -> Chroma.
    Returns the number of chunks stored.
    """
    source_label = source_label or os.path.basename(pdf_path)

    raw_text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(raw_text)
    embeddings = embed_texts(chunks)

    collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": source_label, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    print(f"Ingested {len(chunks)} chunks from '{source_label}' into '{COLLECTION_NAME}'.")
    return len(chunks)


def ingest_text(raw_text: str, source_label: str = "pasted_text") -> int:
    """Same pipeline, but for pasted text input instead of a PDF file."""
    chunks = chunk_text(raw_text)
    embeddings = embed_texts(chunks)

    collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": source_label, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    print(f"Ingested {len(chunks)} chunks from '{source_label}' into '{COLLECTION_NAME}'.")
    return len(chunks)


if __name__ == "__main__":
    # Quick manual test — point this at your NexaFlow PDF
    ingest_pdf("nexaflow_dossier.pdf", source_label="NexaFlow AI Dossier")