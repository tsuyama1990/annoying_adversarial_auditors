import shutil
import subprocess
from typing import Any

from .process_runner import ProcessRunner

# Lazy import to avoid circular dependency or init issues if deps missing
# from .rag.retriever import CodeRetriever


class ToolNotFoundError(Exception):
    pass


class ToolWrapper:
    def __init__(self, command: str):
        self.command = command
        if not shutil.which(command):
            raise ToolNotFoundError(f"Command '{command}' not found in PATH.")
        self.runner = ProcessRunner()

    async def run(
        self,
        args: list[str],
        capture_output: bool = True,
        check: bool = True,
        text: bool = True,
    ) -> subprocess.CompletedProcess[Any]:
        full_cmd = [self.command] + args

        stdout, stderr, returncode = await self.runner.run_command(full_cmd, check=check)

        if check and returncode != 0:
            raise subprocess.CalledProcessError(returncode, full_cmd, output=stdout, stderr=stderr)

        return subprocess.CompletedProcess(
            args=full_cmd,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )


def semantic_code_search(query: str) -> str:
    """
    Search the codebase for relevant functions or classes using semantic search.
    Useful for finding definitions, understanding logic, or checking dependencies.
    """
    from .rag.retriever import CodeRetriever

    try:
        retriever = CodeRetriever()
        results = retriever.search(query)

        if not results:
            return "No relevant code found."

        output = []
        for r in results:
            output.append(
                f"=== {r['type'].upper()}: {r['name']} ({r['file_path']}) ===\n{r['content']}\n"
            )
        return "\n".join(output)
    except Exception as e:
        return f"Search failed: {str(e)}"
