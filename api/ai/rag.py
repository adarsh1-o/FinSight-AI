"""Compatibility adapter to the reusable persistent documentation retriever."""

from typing import Any

from api.assistant.retrieval import DocumentationRetriever


def retrieve_documentation(question: str, limit: int = 4) -> list[dict[str, Any]]:
    results = DocumentationRetriever(top_k=limit).retrieve(question)
    return [
        {
            "source": result["source"],
            "section": result["section"],
            "chunk_id": result["chunk_id"],
            "score": round(result["score"], 4),
            "excerpt": result["text"],
        }
        for result in results
    ]
