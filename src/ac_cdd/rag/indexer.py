import hashlib
from pathlib import Path
from typing import Any

import lancedb
from lancedb.pydantic import LanceModel, Vector
from sentence_transformers import SentenceTransformer
from tree_sitter_languages import get_language, get_parser

from ac_cdd.utils import logger

# Configuration
DB_PATH = Path(".lancedb")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_DIM = 384


class CodeChunk(LanceModel):
    """Schema for code chunks in LanceDB."""

    id: str
    name: str
    type: str  # function, class
    content: str
    docstring: str
    file_path: str
    file_hash: str
    vector: Vector(VECTOR_DIM)  # type: ignore


class CodeIndexer:
    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.db = lancedb.connect(DB_PATH)
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.parser = get_parser("python")
        self.language = get_language("python")

        # Create table if not exists
        try:
            self.table = self.db.create_table("code_chunks", schema=CodeChunk, exist_ok=True)
        except Exception as e:
            # Handle potential schema mismatch or corruption by recreating (simple strategy for now)
            logger.warning(f"Failed to load table, recreating: {e}")
            self.db.drop_table("code_chunks", ignore_missing=True)
            self.table = self.db.create_table("code_chunks", schema=CodeChunk)

    def _get_file_hash(self, file_path: Path) -> str:
        return hashlib.sha256(file_path.read_bytes()).hexdigest()

    def _extract_chunks(self, file_path: Path) -> list[dict[str, Any]]:
        # Read as bytes to handle multi-byte characters correctly with tree-sitter byte offsets
        code_bytes = file_path.read_bytes()
        tree = self.parser.parse(code_bytes)
        root_node = tree.root_node

        chunks = []
        file_hash = self._get_file_hash(file_path)

        def visit(node: Any) -> None:
            if node.type in ("function_definition", "class_definition"):
                name_node = node.child_by_field_name("name")
                if not name_node:
                    return
                # Decode bytes to string for name
                name = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")

                # Extract docstring if present
                docstring = ""
                body = node.child_by_field_name("body")
                if body and body.child_count > 0:
                    first_child = body.children[0]
                    if (
                        first_child.type == "expression_statement"
                        and first_child.children[0].type == "string"
                    ):
                        docstring = code_bytes[
                            first_child.start_byte : first_child.end_byte
                        ].decode("utf-8")

                # Decode content
                content = code_bytes[node.start_byte : node.end_byte].decode("utf-8")

                # Generate ID
                chunk_id = f"{file_path}:{name}:{node.type}"

                chunks.append(
                    {
                        "id": chunk_id,
                        "name": name,
                        "type": "function" if node.type == "function_definition" else "class",
                        "content": content,
                        "docstring": docstring,
                        "file_path": str(file_path),
                        "file_hash": file_hash,
                    }
                )

            for child in node.children:
                visit(child)

        visit(root_node)
        return chunks

    def index(self) -> None:
        logger.info("Indexing codebase...")

        files_processed = 0
        chunks_to_add = []

        # Build map of existing files
        for file_path in self.src_dir.rglob("*.py"):
            if not file_path.is_file():
                continue

            current_hash = self._get_file_hash(file_path)

            # Check if indexed
            # We assume if any chunk exists with same file_path and file_hash, it's up to date.
            existing = self.table.search().where(f"file_path = '{file_path}'").limit(1).to_list()

            if existing and existing[0]["file_hash"] == current_hash:
                continue  # Up to date

            logger.info(f"Indexing {file_path}")

            # Remove old chunks for this file
            self.table.delete(f"file_path = '{file_path}'")

            new_chunks = self._extract_chunks(file_path)
            if not new_chunks:
                continue

            # Embed
            contents = [c["content"] for c in new_chunks]
            vectors = self.model.encode(contents)

            for i, chunk in enumerate(new_chunks):
                chunk["vector"] = vectors[i]
                chunks_to_add.append(chunk)

            files_processed += 1

        if chunks_to_add:
            self.table.add(chunks_to_add)
            logger.info(f"Indexed {files_processed} files, added {len(chunks_to_add)} chunks.")
        else:
            logger.info("Index is up to date.")
