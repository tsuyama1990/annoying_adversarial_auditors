# SPEC.md - Cycle 02: Architect Agent (`gen-cycles` command)

## 1. Summary

This specification document outlines the technical requirements for Cycle 02 of the Autonomous Development Environment (AC-CDD) project. This cycle marks a pivotal transition from the foundational CLI setup to the introduction of the first intelligent, autonomous component: the **Architect Agent**. The central objective of this cycle is to automate the entire project design and planning phase, a task that is traditionally time-consuming, requires significant expertise, and can be a source of ambiguity in software projects. The primary deliverable will be a new CLI command, `gen-cycles`, which will serve as the trigger for this powerful new capability. When a user invokes this command, the system will activate the Architect Agent. This agent's mission is to read and comprehend the high-level, often informal, project requirements provided by the user in the `dev_documents/ALL_SPEC.md` file. It will then synthesize this understanding into a complete, structured, and formal set of architectural documents. This output will be comprehensive, including a high-level `SYSTEM_ARCHITECTURE.md` that describes the project's vision and structure, detailed `SPEC.md` files for each subsequent development cycle, and corresponding `UAT.md` (User Acceptance Test) files that define the "contract" for what success looks like. The successful completion of this cycle will provide a tangible demonstration of the AC-CDD's core value proposition: the ability to translate a simple requirements document into a professional-grade project plan with a single command. It will establish the fundamental patterns for agent-tool interaction, communication with external AI models (specifically Jules), and the generation of file-based artifacts, laying the architectural groundwork for the Coder and Auditor agents to come.

## 2. System Architecture

The architecture for Cycle 02 builds directly upon the foundation laid in Cycle 01, expanding the system to include its first agentic component and the services required to support it. The architecture now bridges the local CLI with a powerful external AI model, orchestrating a flow from local file input to remote AI processing and back to local file output.

**1. Command-Line Interface (CLI):**
The `Typer`-based CLI remains the user's primary entry point. In this cycle, it will be extended to include the new `gen-cycles` command. The role of the CLI in this process is that of an initiator and a status reporter. Upon parsing the `gen-cycles` command, it will be responsible for:
- Instantiating and configuring the core components needed for the workflow, namely the `ArchitectAgent`.
- Triggering the agent's main execution method.
- Providing high-level, real-time feedback to the user via the `ConsolePresenter` service. The user will be kept informed with messages such as "Initializing Architect Agent...", "Reading project requirements from ALL_SPEC.md...", "Communicating with Jules API for architectural generation...", and finally, "Architectural documents generated successfully." This ensures the process is not a "black box" and the user is aware of the system's progress.

**2. Architect Agent:**
This is the new, intelligent core of the system for this cycle. The `ArchitectAgent` is a specialized component designed to orchestrate the entire document generation process. It is not just a simple API wrapper; it is a stateful orchestrator for the architectural task. Its workflow is designed to be robust and methodical:
- **Input Gathering:** It begins by reading the content of two critical files from the local filesystem: the user-provided requirements in `dev_documents/ALL_SPEC.md` and a master instruction set in `dev_documents/ARCHITECT_INSTRUCTION.md`. This master prompt is a key part of the design, as it provides the AI model with its persona, its goals, and, crucially, the strict formatting requirements for its output.
- **Prompt Engineering:** The agent combines the user requirements and the master instructions into a single, coherent, and comprehensive prompt. This step is critical for ensuring the AI model has all the context it needs to produce a high-quality response.
- **AI Invocation:** It then passes this prompt to the `JulesClient` service, delegating the complexities of API communication.
- **Response Parsing:** Upon receiving the raw text response from the client, the agent performs a critical parsing step. It is designed to interpret a specific format in the AI's output (e.g., using `FILENAME: path/to/file.md` as a delimiter) to accurately split the single text block into multiple distinct files and their corresponding content.
- **Artifact Generation:** Finally, it uses a file management tool to write the parsed content to the correct locations on the local filesystem, creating the cycle directories as needed.

**3. Jules Client Service:**
This is a new, dedicated service component whose sole responsibility is to manage all interactions with the Jules API. This abstraction is a critical design choice that decouples the agent's logic from the technical specifics of the API. The `JulesClient` will handle:
- **Authentication:** Securely reading the `JULES_API_KEY` from the configuration and including it in the HTTP headers of every request.
- **Request Formatting:** Constructing the correct JSON payload required by the Jules API endpoint, ensuring the prompt and any other parameters (like model name, temperature) are correctly formatted.
- **HTTP Communication:** Using a robust HTTP library like `httpx` to make the actual POST request to the API, including handling of network timeouts and retries.
- **Response Handling:** Parsing the JSON response from the API, extracting the generated text content, and handling any API-level errors (e.g., authentication failures, rate limiting). It will expose a very simple, high-level method to the agent, such as `generate_text(prompt)`, hiding all the underlying complexity.

**4. Document Writer Tool (within `ProjectManager`):**
Rather than having the agent write directly to the disk, this functionality will be encapsulated within the existing `ProjectManager` service. This service will be enhanced with methods for creating the cycle-specific directories (`dev_documents/CYCLE01`, etc.) and for writing the content to files. This adheres to the Single Responsibility Principle, keeping the agent focused on orchestration and the service focused on the mechanics of filesystem interaction.

The data flow is a clear, linear progression: The user executes `gen-cycles`. The CLI invokes the `ArchitectAgent`. The agent reads local files, constructs a prompt, and sends it to the `JulesClient`. The client communicates with the remote Jules API. The response is returned to the agent, which parses it and uses the `ProjectManager` to write the final document artifacts to the user's local disk.

## 3. Design Architecture

The design for Cycle 02 will be seamlessly integrated into the existing project structure, creating new modules for the agent and client services while extending the CLI.

**1. File and Directory Structure:**
- `dev_src/ac_dd_core/`:
  - `cli.py`: This module will be updated to include a new function, `gen_cycles`, decorated with `@app.command()`.
  - `agents/`: This new directory will house the agent-specific logic.
    - `architect.py`: This new module will contain the `ArchitectAgent` class.
  - `services/`: This directory will be expanded with a new service.
    - `jules.py`: This new module will contain the `JulesClient` class.
    - `project.py`: The existing `ProjectManager` class will be extended with new file and directory management methods.
- `dev_documents/`:
  - `ARCHITECT_INSTRUCTION.md`: A new, critical file will be created. This file will contain the master system prompt for the Architect Agent. It will define the agent's persona, its objectives, the exact list of files it needs to create, and the detailed formatting instructions, including the `FILENAME:` delimiter it must use.

**2. Key Classes and Functions:**
- **`ac_dd_core.cli.py`:**
  - `@app.command()` `def gen_cycles():`: This new function will serve as the entry point for the workflow. It will be responsible for instantiating all the necessary dependencies (`JulesClient`, `ProjectManager`, `ConsolePresenter`) and the `ArchitectAgent` itself. It will then invoke the agent's primary execution method (e.g., `agent.generate_architecture()`) and will use the presenter to communicate progress and success to the user. It will also include robust error handling to catch exceptions from the agent (e.g., file not found, API error) and display them in a user-friendly format.
- **`ac_dd_core.agents.architect.py`:**
  - `class ArchitectAgent:`:
    - `__init__(self, jules_client: JulesClient, project_manager: ProjectManager)`: The constructor will use dependency injection, accepting instances of the client and manager services.
    - `generate_architecture(self) -> None`: This is the main public method that orchestrates the entire process. It will call its private helper methods in sequence.
    - `_build_prompt(self) -> str`: A private method responsible for locating, reading, and combining the contents of `ALL_SPEC.md` and `ARCHITECT_INSTRUCTION.md` into a single string.
    - `_parse_llm_response(self, response: str) -> Dict[str, str]`: A critical private method responsible for parsing the raw output from the LLM. It will be designed to be robust, splitting the response string based on the `FILENAME:` delimiter and populating a dictionary mapping file paths to their string content.
    - The `generate_architecture` method will then iterate over this dictionary and use the `project_manager` to write each file to disk.
- **`ac_dd_core.services.jules.py`:**
  - `class JulesClient:`:
    - `__init__(self, api_key: SecretStr)`: The constructor takes the API key.
    - `generate_text(self, prompt: str, model: str) -> str`: The primary method. It will construct the full JSON payload for the Jules API, including the prompt and model name. It will use `httpx.Client` to make a synchronous POST request, including the API key in the `x-goog-api-key` header. It will check the HTTP response status code and raise custom exceptions for different error conditions (e.g., `JulesAuthenticationError`, `JulesAPIError`). If successful, it will parse the JSON response and return the generated text content.
- **`ac_dd_core.services.project.py`:**
  - `class ProjectManager:`:
    - `create_cycle_directory(self, cycle_number: int) -> None`: A new method that creates a directory like `dev_documents/CYCLE01` if it doesn't already exist.
    - `write_document(self, file_path: Path, content: str) -> None`: A new method for writing content to a given file path, ensuring any necessary parent directories are created.

This design maintains a strong separation of concerns, making the system easier to understand, test, and extend. The agent handles the "what," the client handles the "how" of remote communication, and the manager handles the "how" of local filesystem manipulation.

## 4. Implementation Approach

The implementation will be structured to build the system from its dependencies upwards, ensuring a solid foundation before integrating the components.

**Step 1: Implement the `JulesClient`**
- Create the `JulesClient` class in `ac_dd_core/services/jules.py`.
- The implementation will use the `httpx` library for its robustness and support for timeouts.
- Define custom exception classes (`JulesAuthenticationError`, `JulesAPIError`) to provide more specific error information than a generic `HTTPError`.
- Initially, the method can be tested against a mock HTTP server or by temporarily pointing to a request-capturing service like Webhook.site to inspect the generated requests.

**Step 2: Define the Architect's Master Prompt**
- Create the `dev_documents/ARCHITECT_INSTRUCTION.md` file.
- This file will be carefully crafted. It will be a detailed set of instructions for the LLM, defining its role, the input it will receive, the exact set of output files it must generate, and the precise `FILENAME:` syntax it must use to delimit them. The quality of this prompt is directly proportional to the quality of the generated output.

**Step 3: Enhance the `ProjectManager`**
- Add the new methods (`create_cycle_directory`, `write_document`) to the `ProjectManager` class. These methods will use Python's `pathlib` library for robust and cross-platform path manipulation.

**Step 4: Implement the `ArchitectAgent`**
- Create the `ArchitectAgent` class.
- Implement the `_build_prompt` method first.
- Implement the `_parse_llm_response` method. This will likely use `re.split` or a similar robust method to handle the parsing based on the `FILENAME:` delimiter.
- Implement the main `generate_architecture` method, which will orchestrate the calls to the other methods and services. During development, the `jules_client` can be temporarily mocked to return a hardcoded string, allowing for rapid iteration on the parsing and file-writing logic without incurring API costs.

**Step 5: Integrate into the CLI**
- Add the `gen_cycles` command to `ac_dd_core/cli.py`.
- This function will instantiate the dependencies (reading the API key from `settings` to create the `JulesClient`) and the `ArchitectAgent`.
- It will call the agent's main method and use the `ConsolePresenter` to display status updates.

**Step 6: Write Comprehensive Tests**
- Write unit tests for the `JulesClient` by mocking the `httpx` library, as described in the Test Strategy.
- Write unit tests for the `ArchitectAgent`, providing it with a mocked `JulesClient` and `ProjectManager`. These tests are crucial for verifying the prompt building and, most importantly, the response parsing logic.
- Write a high-level integration test for the `gen-cycles` command using `CliRunner`. This test will mock the `JulesClient` but will interact with a real (temporary) filesystem, asserting that the command correctly creates the expected files and directories based on the mock client's output.

## 5. Test Strategy

The test strategy for Cycle 02 is designed to ensure the reliability of the first AI-driven workflow, focusing on the client-agent interaction and the correctness of the final file-based output.

**Unit Testing Approach:**
- **`JulesClient`:** The client will be tested in isolation by mocking the `httpx` library. We will write several test cases:
  - A "happy path" test where the mock `httpx.post` returns a successful (200 OK) response with a valid JSON payload. We will assert that our client correctly parses this and returns the text content.
  - An authentication error test where the mock returns a 401 or 403 status code. We will assert that our client catches this and raises our custom `JulesAuthenticationError`.
  - A server error test where the mock returns a 500 status code, asserting that a `JulesAPIError` is raised.
  - A test to verify that the `x-goog-api-key` header and the JSON payload are constructed correctly.
- **`ArchitectAgent`:** The agent's logic is critical and will be tested thoroughly with mocked dependencies.
  - The `_build_prompt` method will be tested by creating dummy input files in a temporary directory and asserting that the method's output is the correct concatenation of their contents.
  - The `_parse_llm_response` method will be tested against a variety of sample LLM outputs. This includes perfectly formatted text, text with leading/trailing whitespace, and text with inconsistent newlines, to ensure the parsing logic is resilient. We will assert that it correctly produces the dictionary of file paths and content.
  - The main `generate_architecture` method will be tested by asserting that it calls its dependencies in the correct order (build prompt -> call client -> parse response -> write files). We will use `unittest.mock.Mock` objects for the client and manager and inspect their call history.

**Integration Testing Approach:**
- **CLI to Agent Integration:** We will use the `CliRunner` to invoke the `gen-cycles` command. In this test, we will mock the `ArchitectAgent`'s dependencies (specifically the `JulesClient`) but not the agent itself. This test ensures that the CLI correctly instantiates the agent, injects the dependencies, and calls the agent's main method.
- **End-to-End File Generation Test (Mocked API):** This is the most important test for this cycle. It will verify the entire workflow from the CLI down to the filesystem, with only the external network call being mocked.
  1. The test will set up a temporary directory on the filesystem and create a sample `ALL_SPEC.md` and `ARCHITECT_INSTRUCTION.md` inside it.
  2. It will mock the `JulesClient.generate_text` method, configuring it to return a hardcoded, multi-file string that uses the `FILENAME:` delimiter.
  3. The test will then invoke the `gen-cycles` command using `CliRunner`.
  4. After the command has finished, the test will use `pathlib` to explore the temporary directory.
  5. It will make a series of assertions: that the `SYSTEM_ARCHITECTURE.md` file exists, that the `dev_documents/CYCLE01` directory exists, that the `SPEC.md` and `UAT.md` files exist within it, and, crucially, that the contents of these created files exactly match the corresponding sections from the hardcoded string returned by the mocked client. This test provides extremely high confidence that the entire local orchestration, parsing, and file-writing pipeline is working correctly.
