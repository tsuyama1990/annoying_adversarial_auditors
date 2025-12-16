import lancedb
from sentence_transformers import SentenceTransformer

from .indexer import DB_PATH, EMBEDDING_MODEL_NAME


class CodeRetriever:
    def __init__(self):
        self.db = lancedb.connect(DB_PATH)
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        try:
            self.table = self.db.open_table("code_chunks")
        except Exception:
            # Fallback if table doesn't exist yet (e.g. before first index)
            self.table = None

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.table:
            return []

        query_vector = self.model.encode(query)
        results = self.table.search(query_vector).limit(top_k).to_list()

        # Format for Agent
        formatted_results = []
        for r in results:
            formatted_results.append(
                {
                    "name": r["name"],
                    "type": r["type"],
                    "file_path": r["file_path"],
                    "docstring": r["docstring"],
                    "content": r["content"],
                    # LanceDB returns distance usually, strictly lower is better for L2
                    "score": r.get("_distance", 0.0),
                }
            )
        return formatted_results
