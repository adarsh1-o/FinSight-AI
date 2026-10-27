"""Run with ``python -m api.assistant.index_documents`` to rebuild the RAG index."""

from .retrieval import build_index


def main() -> None:
    result = build_index()
    print(f"Indexed {result['chunks']} chunks from {result['documents']} Markdown documents.")


if __name__ == "__main__":
    main()
