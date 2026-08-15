import os
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
EMBED_MODEL = "openai/text-embedding-3-small"

# ... rest of the file stays exactly the same


def embed_query(query: str) -> list[float]:
    response = client.embeddings.create(model=EMBED_MODEL, input=[query])
    return response.data[0].embedding


def retrieve_context(query: str, top_k: int = 5) -> list[str]:
    """
    The main function other modules call.
    Given a natural-language query, returns the top_k most relevant
    chunks of company knowledge as plain strings.
    """
    collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    query_embedding = embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    documents = results.get("documents", [[]])[0]
    return documents


def retrieve_context_with_sources(query: str, top_k: int = 5) -> list[dict]:
    """
    Same as retrieve_context, but also returns source metadata —
    useful if you want to show citations or debug retrieval quality.
    """
    collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    query_embedding = embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    return [{"text": doc, "source": meta.get("source"), "chunk_index": meta.get("chunk_index")}
            for doc, meta in zip(documents, metadatas)]


if __name__ == "__main__":
    # Quick manual test
    test_query = "What is the pricing for the WhatsApp AI Assistant?"
    context = retrieve_context(test_query)
    print(f"Query: {test_query}\n")
    for i, chunk in enumerate(context, 1):
        print(f"--- Result {i} ---\n{chunk[:300]}...\n")