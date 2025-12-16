import difflib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ..domain_models import FileCreate, FileOperation, FilePatch
from ..utils import logger

if TYPE_CHECKING:
    from ..domain_models import FileOperation


class FilePatcher:
    """
    Handles file operations including reading, writing, and patching files
    with fuzzy matching support.
    """

    def apply_changes(
        self, changes: list[FileOperation], dry_run: bool = False, interactive: bool = False
    ) -> None:
        """
        Applies a list of FileOperation objects to the file system.
        """
        console = Console()
        is_tty = sys.stdout.isatty()

        for op in changes:
            p = Path(op.path)
            new_content = ""
            diff_text = ""

            if isinstance(op, FileCreate):
                if p.exists():
                    old_content_lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
                else:
                    old_content_lines = []

                new_content = op.content
                new_content_lines = new_content.splitlines(keepends=True)

                diff = list(
                    difflib.unified_diff(
                        old_content_lines,
                        new_content_lines,
                        fromfile=str(p),
                        tofile=str(p),
                        lineterm="",
                    )
                )
                diff_text = "".join(diff)

            elif isinstance(op, FilePatch):
                if not p.exists():
                    logger.error(f"Cannot patch non-existent file: {p}")
                    continue

                original_content = p.read_text(encoding="utf-8")
                start_idx, end_idx = self._fuzzy_find(original_content, op.search_block)

                if start_idx == -1:
                    logger.error(
                        f"Patch failed for {p}: search_block not found (Exact match required)."
                    )
                    continue

                new_content = (
                    original_content[:start_idx] + op.replace_block + original_content[end_idx:]
                )

                old_content_lines = original_content.splitlines(keepends=True)
                new_content_lines = new_content.splitlines(keepends=True)

                diff = list(
                    difflib.unified_diff(
                        old_content_lines,
                        new_content_lines,
                        fromfile=str(p),
                        tofile=str(p),
                        lineterm="",
                    )
                )
                diff_text = "".join(diff)

            # Interactive Review
            if interactive and is_tty and not dry_run:
                console.print(
                    Panel(f"Proposed changes for [bold]{p}[/bold] ({op.operation})", style="blue")
                )
                if diff_text:
                    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
                    console.print(syntax)
                else:
                    console.print(
                        f"[yellow]New File (Full Content):[/yellow]\n{new_content[:500]}..."
                    )

                should_apply = typer.confirm(f"Apply changes to {p}?", default=True)
                if not should_apply:
                    logger.warning(f"Skipped changes for {p}")
                    continue

            # Apply
            if not dry_run:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(new_content, encoding="utf-8")
                logger.info(f"Applied {op.operation} to {p}")
            else:
                logger.info(f"[DRY-RUN] Would apply {op.operation} to {p}")

    def read_src_files(self, src_dir: str) -> str:
        """
        Reads all python files in the source directory, respecting .auditignore.
        Returns a formatted string of file contents.
        """
        import fnmatch

        ignored_patterns = {"__pycache__", ".git", ".env", ".DS_Store", "*.pyc"}
        auditignore_path = Path(".auditignore")
        if auditignore_path.exists():
            try:
                lines = auditignore_path.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ignored_patterns.add(line)
            except Exception as e:
                logger.warning(f"Failed to read .auditignore: {e}")

        content_str = ""
        path = Path(src_dir)
        for p in path.rglob("*"):
            if p.is_file():
                is_ignored = False
                for pattern in ignored_patterns:
                    if fnmatch.fnmatch(p.name, pattern) or fnmatch.fnmatch(str(p), pattern):
                        is_ignored = True
                        break
                    if pattern in str(p):
                        is_ignored = True
                        break

                if not is_ignored:
                    try:
                        file_content = p.read_text(encoding="utf-8")
                        content_str += f"\n=== {p} ===\n{file_content}"
                    except Exception as e:
                        logger.warning(f"Skipping {p}: {e}")
        return content_str

    def _fuzzy_find(self, content: str, block: str) -> tuple[int, int]:
        """
        Finds the block in content with fuzzy matching (ignoring whitespace).
        Returns (start_index, end_index) or (-1, -1) if not found.
        """
        idx = content.find(block)
        if idx != -1:
            return idx, idx + len(block)

        content_lines = content.splitlines(keepends=True)
        block_lines = block.splitlines(keepends=True)

        norm_content = [line.strip() for line in content_lines]
        norm_block = [line.strip() for line in block_lines]

        n_block = len(norm_block)
        n_content = len(norm_content)

        if n_block == 0:
            return -1, -1

        for i in range(n_content - n_block + 1):
            if norm_content[i : i + n_block] == norm_block:
                start_char = sum(len(line) for line in content_lines[:i])
                end_char = sum(len(line) for line in content_lines[: i + n_block])
                return start_char, end_char

        return -1, -1
