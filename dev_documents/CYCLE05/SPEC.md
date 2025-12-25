# Cycle 05: Finalisation - Specification Document

**Version:** 1.0.0
**Status:** Final
**Cycle:** 05
**Title:** User Interface, Optimisation, and Packaging

## 1. Summary

This document provides the detailed technical specification for the fifth and final development cycle of the MLIP-AutoPipe project. With the core autonomous functionality now complete, this cycle focuses on turning the powerful backend into a polished, usable, and robust tool for the end-user, the computational materials scientist. The primary objectives are threefold: 1) to create a clean, professional, and user-friendly command-line interface (CLI); 2) to conduct performance profiling and optimization to ensure the tool is efficient; and 3) to package the entire application for easy distribution and installation, complete with comprehensive user documentation. This cycle is less about adding new scientific features and more about the crucial software engineering work required to make a complex system accessible, reliable, and maintainable.

The first major task is the development of a high-quality CLI. The current interaction method, running specific Python scripts, is suitable for development but not for a finished product. We will build a proper CLI using a modern framework like `Typer` or `Click`. This will provide a single, clear entry point (`mlip-pipe`) with well-defined commands (e.g., `run`, `analyze`), arguments, and options. The CLI will include features like progress bars for long-running tasks, different levels of verbosity controlled by flags (e.g., `-v`, `--verbose`), and robust error handling that provides clear, actionable feedback to the user instead of raw Python tracebacks. This professional interface is essential for user adoption and for making the tool feel like a mature piece of scientific software.

The second focus is performance. The pipeline, particularly the exploration module (Module B) and the simulation engine (Module E), involves intensive computation and data processing. This task involves a systematic profiling of the entire workflow to identify any performance bottlenecks. Using tools like `cProfile` and `py-spy`, we will analyze CPU and memory usage to find inefficient code sections—for example, slow loops in data processing or suboptimal data structures. We will then refactor these sections, applying techniques like vectorization with NumPy, further optimization with Numba, or more efficient I/O handling, to ensure the application runs as fast as possible. The final part of this cycle is dedicated to documentation and packaging. We will write a comprehensive user guide, including a "Getting Started" tutorial, detailed explanations of the `input.yaml` file format, and examples. The entire project will then be configured for packaging using standard Python tools and its `pyproject.toml` file, allowing a user to install it easily and reliably on their system with a single command: `pip install mlip-autopipec`.

## 2. System Architecture

The architecture in Cycle 05 does not introduce new computational modules, but rather adds a crucial "presentation layer" on top of the existing system: the Command-Line Interface. This layer serves as the sole entry point for the user and acts as a user-friendly façade for the powerful but complex `WorkflowOrchestrator` developed in the previous cycles.

The final user interaction flow is as follows:
1.  **User Command:** The user types a command in their terminal, e.g., `mlip-pipe run --verbose input.yaml`.
2.  **CLI Application:** The `Typer`/`Click` application parses this command. It validates the arguments (e.g., does `input.yaml` exist?) and maps the command and options to a specific function call.
3.  **Orchestrator Invocation:** The CLI application instantiates and configures the main `WorkflowOrchestrator`. It passes the verbosity level to the orchestrator's logging configuration and provides the path to the `input.yaml` file.
4.  **Backend Execution:** The `WorkflowOrchestrator` takes over and executes the entire active learning pipeline, as developed in Cycles 01-04. The orchestrator's logging and progress reporting are now displayed to the user through the CLI's output.
5.  **Exit and Status:** Once the orchestrator completes its run, it returns a success or failure status to the CLI application, which then exits with an appropriate status code, allowing it to be used in automated scripting.

This architecture cleanly separates the user interface logic from the core scientific workflow logic. The `WorkflowOrchestrator` remains unaware of the CLI, which ensures that the core engine can still be imported and used as a library in other Python scripts if needed, providing maximum flexibility.

**Architectural Placement:**

```mermaid
graph TD
    A[User @ Terminal] --1. types command--> B[CLI Application (Typer/Click)];
    B --2. Parses & Validates--> C[Instantiate & Configure];
    C --3. Invokes--> D{Workflow Orchestrator (from Cycle 04)};
    D --4. Executes Entire Backend Pipeline--> E[Core Modules A-E];
    E --5. Reports Progress/Logs--> D;
    D --6. Returns Status--> B;
    B --7. Displays Output & Exits--> A;

    subgraph "New in Cycle 05"
        B;
    end

    subgraph "Existing System"
        D; E;
    end

    style B fill:#9f9,stroke:#333,stroke-width:2px
```

The documentation and packaging aspects of this cycle are meta-level architectural concerns. They define how the software is presented to the user and how its components are bundled together for distribution, but do not alter the runtime interaction between the core modules.

## 3. Design Architecture

The design for Cycle 05 focuses on the user-facing aspects of the application.

**File and Class Structure:**

```
mlip_autopipec/
├── cli.py                     # The main Typer/Click application
├── orchestrator_cycle04.py    # (Final orchestrator)
├── ...                        # All other modules and utils
└── pyproject.toml             # (Heavily modified for packaging)

docs/
├── source/
│   ├── conf.py                # Sphinx configuration
│   ├── index.rst              # Main page
│   ├── tutorial.rst           # Getting started guide
│   └── input_format.rst       # Detailed config explanation
└── ...
```

**Class and API Definitions:**

1.  **`cli.py`**: This file will contain the entire CLI definition. `Typer` is preferred for its modern, type-hint-based design.
    ```python
    import typer
    from typing_extensions import Annotated
    import logging

    # Rich can be used for better formatting
    from rich.console import Console

    app = typer.Typer()
    console = Console()

    @app.command()
    def run(
        config_file: Annotated[typer.Path(exists=True), typer.Argument(help="Path to the minimal input.yaml file.")],
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable detailed logging output.")] = False
    ):
        """
        Run the full MLIP-AutoPipe workflow.
        """
        level = logging.DEBUG if verbose else logging.INFO
        # Configure logging...

        try:
            console.print("[bold green]Starting MLIP-AutoPipe workflow...[/bold green]")
            # orchestrator = WorkflowOrchestrator(...)
            # orchestrator.execute()
            console.print("[bold green]Workflow completed successfully![/bold green]")
        except Exception as e:
            console.print(f"[bold red]An error occurred: {e}[/bold red]")
            raise typer.Exit(code=1)

    @app.command()
    def analyze(...):
        """(Future extension) Analyze results from a completed run."""

    if __name__ == "__main__":
        app()
    ```

2.  **`pyproject.toml` Configuration**: This file will be significantly expanded to support packaging and CLI entry points.
    ```toml
    [project]
    name = "mlip-autopipec"
    version = "1.0.0"
    # ... other metadata ...
    dependencies = [
        "ase", "typer[all]", "rich", ...
    ]

    [project.scripts]
    mlip-pipe = "mlip_autopipec.cli:app"

    [tool.setuptools.packages.find]
    where = ["."]
    ```

**Performance Profiling Design:**
The optimization process will be systematic. We will use `cProfile` to get a high-level overview of which functions are taking the most time.
```bash
python -m cProfile -o profile.pstats -m mlip_autopipec.cli run input.yaml
```
Then, we will use a visualizer like `snakeviz` to analyze `profile.pstats`. For more granular, line-by-line analysis of CPU-bound functions (like the descriptor calculations), we can use `line_profiler`. Any identified bottlenecks will be refactored for better performance.

## 4. Implementation Approach

The implementation will be done in three parallel streams: CLI development, documentation writing, and performance optimization.

**Step 1: CLI Development**
1.  **Framework Setup:** Choose and install the CLI framework (`Typer` is recommended). Create the `cli.py` file and define the main `app` object and the primary `run` command.
2.  **Orchestrator Integration:** In the `run` command, add the code to instantiate and execute the `WorkflowOrchestrator`.
3.  **Argument Parsing and Logging:** Implement the `--verbose` flag and connect it to Python's `logging` module to control the level of detail in the console output.
4.  **User Feedback:** Integrate the `rich` library to add progress bars for long loops (like structure labelling) and to format output with colors for better readability (e.g., green for success, red for errors).
5.  **Error Handling:** Wrap the main orchestrator call in a `try...except` block to catch any exceptions. Instead of letting the program crash, this block will print a user-friendly error message and exit with a non-zero status code.

**Step 2: Documentation**
1.  **Tool Selection:** Set up `Sphinx` or `MkDocs` in the `docs/` directory. Sphinx is more powerful, while MkDocs is simpler.
2.  **Getting Started Guide:** Write a `tutorial.rst` page. This will be a step-by-step guide that walks a new user through installing the package and running their first simple example (e.g., for bulk Silicon).
3.  **Configuration Reference:** Write the `input_format.rst` page. This will be a detailed reference explaining every possible key and section in the `input.yaml` file, what they do, and their allowed values.
4.  **API Docs (Optional):** Configure Sphinx's `autodoc` extension to automatically generate documentation from the code's docstrings, creating a reference for advanced users or developers who might want to extend the tool.

**Step 3: Performance Optimization**
1.  **Create Benchmark Case:** Prepare a standard `input.yaml` and test system that is complex enough to be representative but fast enough to be run repeatedly. This will be our benchmark.
2.  **Profile:** Run the profiler (`cProfile`) on the benchmark case and save the results.
3.  **Analyze:** Use `snakeviz` to visualize the profiling results and identify the top 3-5 most time-consuming functions in the application.
4.  **Refactor:** For each identified bottleneck, analyze the code and apply appropriate optimizations. For example:
    *   If a loop in Python is slow, try to rewrite it using vectorized NumPy operations.
    *   If NumPy is already used but it's still slow, rewrite the function as a Numba-jitted function.
    *   If I/O is slow, check for opportunities to read/write data in larger chunks.
5.  **Re-benchmark:** After each significant refactoring, re-run the profiler on the benchmark case to confirm that the change has resulted in a measurable performance improvement.

**Step 4: Packaging**
1.  **Update `pyproject.toml`:** Finalize the `pyproject.toml` file. This includes defining the project name, version, dependencies, and, most importantly, the `[project.scripts]` entry point to create the `mlip-pipe` command.
2.  **Build and Test Installation:** Run `pip install .` in the project root to test the local installation. This should make the `mlip-pipe` command available in the environment. Run the command to ensure it works.
3.  **Create Source Distribution:** Run the build command (e.g., `python -m build`) to create the final, distributable package files (`.tar.gz` and `.whl`).

## 5. Test Strategy

Testing in Cycle 05 focuses on the new user-facing layer and the overall robustness of the final application.

**Unit Testing:**

*   **CLI Tests:** The CLI will be tested using the framework's recommended testing tools (e.g., `Typer`'s `CliRunner`).
    *   Test that calling `mlip-pipe run` with a non-existent file path correctly exits with an error message.
    *   Test that the `--verbose` flag correctly sets the logging level.
    *   Test that `mlip-pipe --help` displays the help message and exits successfully.
    *   We will use `pytest-mock` to mock the `WorkflowOrchestrator` itself, so we can test the CLI's argument parsing and error handling logic in isolation without running the entire backend.

**Integration Testing:**

*   **Installation Test:** A test script will be created (potentially for a CI/CD pipeline) that:
    1.  Creates a clean virtual environment.
    2.  Installs the packaged `.whl` file into it.
    3.  Runs `mlip-pipe --help` and checks the output.
    4.  Runs a very short E2E test case using the installed `mlip-pipe` command.
    *   This test validates that the packaging and installation process is working correctly.

**End-to-End (E2E) Testing:**

*   **Final Validation Suite:** The existing E2E tests from previous cycles will be refactored to be run via the new `mlip-pipe` CLI command instead of by calling the Python scripts directly. This will serve as the final validation for the entire integrated application. We will run the "successful alloy" and "successful molecule" test cases from the CLI to ensure no regressions have been introduced.
*   **Documentation Test:** A human-driven test where a developer (other than the one who wrote the docs) attempts to follow the `tutorial.rst` from scratch on a clean machine. Their ability to successfully complete the tutorial without confusion will be the measure of the documentation's quality.
