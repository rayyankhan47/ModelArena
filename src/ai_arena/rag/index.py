"""RAG document upload helpers for Backboard."""

from pathlib import Path
from typing import Dict, List

from ai_arena.orchestrator.backboard_client import BackboardClient


def load_corpus_files() -> List[Path]:
    """Return all corpus files to upload."""
    base = Path(__file__).parent / "corpus"
    return [base / "rules.md", base / "strategy.md"]


def upload_corpus_to_assistant(client: BackboardClient, assistant_id: str) -> Dict[str, str]:
    """Upload corpus documents to a Backboard assistant.

    Returns a map of filename -> document_id.
    """
    doc_ids: Dict[str, str] = {}
    for path in load_corpus_files():
        with open(path, "rb") as f:
            file_tuple = (path.name, f.read(), "text/markdown")
            resp = client.upload_document_to_assistant(assistant_id, file_tuple)
            doc_ids[path.name] = resp.get("document_id", "")
    return doc_ids


def upload_corpus_to_thread(client: BackboardClient, thread_id: str) -> Dict[str, str]:
    """Upload corpus documents to a Backboard thread."""
    doc_ids: Dict[str, str] = {}
    for path in load_corpus_files():
        with open(path, "rb") as f:
            file_tuple = (path.name, f.read(), "text/markdown")
            resp = client.upload_document_to_thread(thread_id, file_tuple)
            doc_ids[path.name] = resp.get("document_id", "")
    return doc_ids
