from pathlib import Path

import pytest

from api.ai.intent import Intent, detect_intent
from api.assistant.embeddings import EmbeddingError, LocalTextEmbedder
from api.assistant.ingestion import MarkdownDocument, chunk_documents, load_markdown_documents
from api.assistant.retrieval import DocumentationRetriever, build_index
from api.assistant.vector_store import SQLiteVectorStore
from api.ai.prompts import SYSTEM_PROMPT


@pytest.fixture
def sample_docs(tmp_path):
    isolation = tmp_path / "methods.md"
    isolation.write_text(
        "# Anomaly Detection\n\nThe project uses Isolation Forest for anomaly detection. "
        "Its contamination setting is 0.05.\n\n"
        "# Customer Segmentation\n\nCustomer segmentation uses K-Means clustering after "
        "StandardScaler feature scaling.",
        encoding="utf-8",
    )
    return [isolation]


def test_load_markdown_missing_and_empty_documents(tmp_path):
    missing = tmp_path / "missing.md"
    empty = tmp_path / "empty.md"
    empty.write_text("  \n", encoding="utf-8")
    assert load_markdown_documents([missing, empty]) == []


def test_loads_the_two_approved_project_documents():
    documents = load_markdown_documents()
    assert {document.path for document in documents} == {
        "docs/ai_assistant.md", "docs/data_dictionary.md"
    }


def test_ingestion_preserves_heading_metadata_and_stable_ids(sample_docs):
    documents = load_markdown_documents(sample_docs)
    first = chunk_documents(documents)
    second = chunk_documents(documents)
    assert len(first) == 2
    assert first[0].section == "Anomaly Detection"
    assert first[0].source.endswith("methods.md")
    assert first[0].chunk_id == second[0].chunk_id
    assert first[0].document_id == second[0].document_id


def test_chunking_splits_long_sections_with_bounded_overlap():
    content = "# Long Section\n\n" + "Important methodology detail. " * 50
    chunks = chunk_documents([MarkdownDocument("fixture.md", content)], chunk_size=180, chunk_overlap=25)
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 180 for chunk in chunks)
    assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))
    assert set(chunks[0].text.split()) & set(chunks[1].text.split())


def test_chunking_rejects_invalid_settings():
    with pytest.raises(ValueError):
        chunk_documents([MarkdownDocument("doc.md", "# Title\n\nwords")], chunk_size=100, chunk_overlap=100)


def test_embedding_interface_has_fixed_dimensions_and_validates_input():
    model = LocalTextEmbedder(dimensions=512)
    vector = model.embed_one("Isolation Forest anomaly detection")
    assert vector.shape == (1, 512)
    assert vector.nnz > 0
    with pytest.raises(EmbeddingError):
        model.embed([" "])
    with pytest.raises(EmbeddingError):
        model.embed_one("!!!")


def test_sqlite_store_reindexes_without_duplicates_and_removes_old_rows(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    model = LocalTextEmbedder(dimensions=512)
    first_chunks = chunk_documents([MarkdownDocument("a.md", "# A\n\nalpha method")])
    store.replace_all([chunk.as_dict() for chunk in first_chunks], model.embed([first_chunks[0].text]))
    store.replace_all([chunk.as_dict() for chunk in first_chunks], model.embed([first_chunks[0].text]))
    assert store.count() == 1

    changed = chunk_documents([MarkdownDocument("b.md", "# B\n\nbeta method")])
    store.replace_all([chunk.as_dict() for chunk in changed], model.embed([changed[0].text]))
    assert store.count() == 1
    result = store.search(model.embed_one("beta method"), top_k=2)
    assert result[0]["source"] == "b.md"

    store.replace_all([], [])
    assert store.count() == 0
    assert store.search(model.embed_one("beta method")) == []


def test_retriever_selects_the_matching_document_and_source(sample_docs, tmp_path):
    store = SQLiteVectorStore(tmp_path / "rag.sqlite3")
    build_index(paths=sample_docs, store=store, embedder=LocalTextEmbedder(dimensions=2048))
    retriever = DocumentationRetriever(store=store, embedder=LocalTextEmbedder(dimensions=2048), top_k=1, auto_index=False)

    anomaly = retriever.retrieve("Which algorithm is used for anomaly detection?")
    segmentation = retriever.retrieve("Which algorithm is used for customer segmentation?")
    assert "Isolation Forest" in anomaly[0]["text"]
    assert anomaly[0]["source"].endswith("methods.md")
    assert "K-Means" in segmentation[0]["text"]


def test_empty_retrieval_returns_no_results(tmp_path):
    store = SQLiteVectorStore(tmp_path / "empty.sqlite3")
    retriever = DocumentationRetriever(store=store, auto_index=False)
    assert retriever.retrieve("Which algorithm does the project use?") == []
    with pytest.raises(ValueError):
        retriever.retrieve("  ")


def test_retriever_rebuilds_when_a_source_document_changes(tmp_path):
    source = tmp_path / "changing.md"
    source.write_text("# Topic\n\nFirst explanation about account balances.", encoding="utf-8")
    store = SQLiteVectorStore(tmp_path / "refresh.sqlite3")
    model = LocalTextEmbedder(dimensions=512)
    build_index(paths=[source], store=store, embedder=model)
    source.write_text("# Topic\n\nUpdated explanation about account balances and limits.", encoding="utf-8")
    retriever = DocumentationRetriever(store=store, embedder=model, paths=[source])
    assert "Updated explanation" in retriever.retrieve("account balance limits")[0]["text"]
    source.unlink()
    assert retriever.retrieve("account balance limits") == []
    assert store.count() == 0


def test_question_intent_routes_docs_and_analytics_separately():
    assert detect_intent("Which algorithm is used for customer segmentation?") is Intent.DOCUMENTATION
    assert detect_intent("What is the total transaction amount?") is Intent.KPI
    assert detect_intent("What does transaction_date mean?") is Intent.DOCUMENTATION


def test_grounded_prompt_requires_uncertainty_and_rejects_anomaly_as_fraud():
    assert "If the evidence does not answer the question, say so" in SYSTEM_PROMPT
    assert "Similarity is only a retrieval hint" in SYSTEM_PROMPT
    assert "never call them confirmed fraud" in SYSTEM_PROMPT
