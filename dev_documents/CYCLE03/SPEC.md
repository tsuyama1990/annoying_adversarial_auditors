# SPEC.md - Cycle 03: Coder Agent and Sandbox Execution (`run-cycle` command)

## 1. Summary

This specification provides the detailed technical requirements for Cycle 03 of the Autonomous Development Environment (AC-CDD) project. This cycle marks a monumental leap in the system's capabilities, moving beyond the realm of planning and documentation into the domain of active, hands-on code generation and execution. The central objective of this cycle is to construct the core implementation engine of the entire framework. This will be accomplished by developing and integrating two revolutionary components: the **Coder Agent**, an AI agent tasked with translating specifications into high-quality source code, and the **Secure Sandbox Environment**, a fully isolated and ephemeral container where all code-related activities will occur. The primary deliverable for this cycle is a new, powerful CLI command: `run-cycle --id <cycle_id>`. When a user invokes this command, the system will initiate a sophisticated, automated workflow. It will begin by reading the "contract" for the specified cycle—the `SPEC.md` file generated in Cycle 02. It will then provision a pristine, secure E2B sandbox environment, synchronize the project's existing source code into it, and then deploy the Coder Agent to carry out the implementation tasks as laid out in the specification. Once the agent has completed its work, the newly generated or modified code will be securely synchronized back to the user's local filesystem. The integration of the E2B sandbox is a cornerstone of this cycle and the entire AC-CDD philosophy, providing a secure, reproducible, and dependency-free environment that is completely decoupled from the user's local machine, thereby eliminating a whole class of common development frustrations. This cycle is the heart of the project, turning the architectural blueprint into tangible, running code.

## 2. System Architecture

The architecture for Cycle 03 introduces a critical new dimension to the system: a remote execution environment. This necessitates the creation of services to manage this environment and a new agent that can operate within it. The system now spans both the local machine and a cloud-based sandbox.

**1. Command-Line Interface (CLI):**
The `Typer`-based CLI will be extended with the `run-cycle` command. This command will require a `--id` option to specify which development cycle's contract should be executed. The CLI's role in this more complex workflow is that of a high-level orchestrator and user-feedback provider. It will be responsible for:
- Parsing the command and its arguments.
- Instantiating and initiating the `LangGraph` orchestrator that manages the coding workflow.
- Using the `ConsolePresenter` to provide the user with clear, step-by-step status updates throughout the process, which is crucial given the multiple stages involved (e.g., "Provisioning secure E2B sandbox...", "Synchronizing local source code to sandbox...", "Coder Agent is now implementing features...", "Synchronization complete.").

**2. LangGraph Orchestrator:**
To manage the multi-step process of this cycle, we will formally introduce `LangGraph` as the workflow's state machine. For this initial implementation, the graph will be linear, but it will establish the pattern for the more complex, cyclical graph in later stages. The graph will define the following states (nodes):
- `SETUP_SANDBOX`: This initial node will be responsible for creating the sandbox instance via the `SandboxRunner` service and performing the initial synchronization of the project's `src/` directory into the sandbox.
- `CODING`: This node will invoke the `CoderAgent`, providing it with the cycle's specification and the tools it needs to interact with the sandbox.
- `SYNC_BACK_AND_TEARDOWN`: This final node will be responsible for copying the modified source code from the sandbox back to the user's local filesystem and then ensuring the sandbox instance is properly destroyed to conserve resources.

**3. Coder Agent:**
The Coder Agent is the star of this cycle. It is an intelligent, tool-using AI component that performs the actual software development. Its defining characteristic is that it operates *exclusively* within the confines of the secure sandbox. Its internal workflow is as follows:
- It is initialized with the content of the `dev_documents/CYCLE{xx}/SPEC.md`, which serves as its set of instructions.
- It is provided with a toolkit of functions that allow it to interact with the sandbox's filesystem (e.g., `list_files`, `read_file`, `write_file`, `patch_file`).
- It uses the `JulesClient` to communicate with a powerful code-generation LLM. It will engage in a "conversation" with the model, sending the specification and, when necessary, the content of existing files for context. The model's responses will include not just code, but also the instructions for which tools to use to apply that code. The agent parses these instructions and executes the corresponding file operations within the sandbox.

**4. E2B Sandbox Runner (`SandboxRunner` Service):**
This is a new, critical infrastructure service that will abstract away all the complexities of interacting with the E2B sandbox. This service will be a robust, stateful class that manages the entire lifecycle of a single sandbox session. Its key responsibilities include:
- **Lifecycle Management:** It will handle the creation (`start()`) and destruction (`close()`) of the sandbox instance, using the `E2B_API_KEY` from the configuration for authentication.
- **File Synchronization:** This is one of its most critical roles. It will implement a `sync_to_sandbox` method that intelligently packages the user's local `src/` directory (e.g., by creating an in-memory tarball), uploads this single archive to the sandbox, and then executes a command to extract it. This is far more efficient than uploading files one by one. It will also implement the reverse `sync_from_sandbox` process.
- **Tool Implementation:** It will provide the concrete implementations of the tools that the Coder Agent uses, such as `write_file`, `read_file`, and `list_files`. These methods will directly translate the agent's requests into commands for the `e2b` Python SDK.
- **Command Execution:** It will provide a generic `execute_command` method that can run any arbitrary shell command inside the sandbox. While this is primarily for future cycles (like running `pytest`), it's a core capability of the sandbox that will be built in this cycle.

The data flow is a clear, orchestrated sequence: The user runs `run-cycle`. The CLI starts the `LangGraph`. The `SETUP_SANDBOX` node uses the `SandboxRunner` to create the environment and sync the code *to* it. The `CODING` node unleashes the `CoderAgent` to work within the sandbox. Finally, the `SYNC_BACK_AND_TEARDOWN` node uses the `SandboxRunner` to sync the modified code back *from* the sandbox before destroying it.

## 3. Design Architecture

The design will focus on creating the robust `SandboxRunner` service and ensuring the `CoderAgent` has a clean interface for interacting with it, all orchestrated by a `LangGraph`.

**1. File and Directory Structure:**
- `dev_src/ac_dd_core/`:
  - `cli.py`: The `run_cycle` command function will be added here.
  - `agents/coder.py`: This new module will contain the `CoderAgent` class.
  - `services/sandbox.py`: This new module will contain the `SandboxRunner` class.
  - `graph.py`: This new module will define the `LangGraph` workflow, state, and node functions for the `run-cycle` command.
- `src/`: The contents of this directory are now of primary importance, as they are the target of the synchronization operations.

**2. Key Classes and Functions:**
- **`ac_dd_core.cli.py`:**
  - `@app.command()` `def run_cycle(id: str):`: The CLI command function. Its main responsibility will be to read the content of the appropriate `SPEC.md` file and use it to initialize and run the `LangGraph` workflow.
- **`ac_dd_core.graph.py`:**
  - `CycleState` (TypedDict): A dictionary-like object to hold the state of the workflow, including the `spec_content`, the `sandbox_runner` instance, and a list of `modified_files`.
  - `class CoderWorkflow:`: A class that encapsulates the `LangGraph` construction.
    - It will define the node functions: `_setup_sandbox_node`, `_coder_agent_node`, and `_sync_back_node`. Each of these functions will take the `CycleState` as input and return an updated `CycleState`.
    - It will have a `build_graph()` method that uses `langgraph.graph.StateGraph` to assemble these nodes and define the edges that connect them in a linear sequence.
- **`ac_dd_core.agents.coder.py`:**
  - `class CoderAgent:`:
    - `__init__(self, jules_client: JulesClient, sandbox: SandboxRunner)`: The constructor takes the API client and, crucially, an *active* instance of the `SandboxRunner`.
    - `run(self, spec_content: str) -> List[str]`: The main execution method. It will construct a master prompt that includes the specification and a detailed description of the available filesystem tools. It will then enter into a conversational loop with the Jules LLM, processing the model's responses to execute the requested tool calls. It will keep track of all files it modifies and return this list upon completion.
- **`ac_dd_core.services.sandbox.py`:**
  - `class SandboxRunner:`:
    - `__init__(self, api_key: SecretStr)`: The constructor.
    - `start(self) -> None`: Uses `e2b.Sandbox()` to create the sandbox instance. Designed to be used in a `with` statement.
    - `sync_to_sandbox(self, local_path: Path) -> None`: Implements the tarball-based upload and extraction.
    - `sync_from_sandbox(self, local_path: Path) -> None`: Implements the tarball-based download and extraction.
    - `write_file(self, remote_path: str, content: str) -> None`: Implements the tool for writing a file using the `e2b` SDK.
    - `read_file(self, remote_path: str) -> str`: Implements the tool for reading a file.
    - `list_files(self, remote_path: str) -> List[str]`: Implements the tool for listing files.
    - `close(self) -> None`: Calls the underlying `sandbox.close()` method.

This architecture ensures a strong separation of concerns. The `SandboxRunner` is a low-level, reusable infrastructure component. The `CoderAgent` contains the high-level, intelligent logic for a specific task. The `LangGraph` defines the overall process flow, and the `CLI` is the simple entry point for the user.

## 4. Implementation Approach

The implementation will be tackled in a logical order, starting with the most complex and foundational new piece: the `SandboxRunner`.

**Step 1: Implement the `SandboxRunner` Service**
- Create the `SandboxRunner` class in `ac_dd_core/services/sandbox.py`.
- Use the `e2b` Python SDK as the primary dependency. The class should be designed as a context manager (using `__enter__` and `__exit__`) to ensure that the `start()` and `close()` methods are reliably called.
- For `sync_to_sandbox`, use Python's built-in `tarfile` library to create a `BytesIO` in-memory tarball of the `src/` directory. Use the `e2b` SDK's `filesystem.write_bytes` to upload this tarball, and then `sandbox.process.start_and_wait('tar -xzf ...')` to extract it.
- Implement the agent tool methods (`write_file`, `read_file`, etc.) as direct wrappers around the corresponding `sandbox.filesystem` methods.
- The `sync_from_sandbox` method will reverse the process, executing `tar -czf ...` inside the sandbox and using `filesystem.read_bytes` to download the archive.

**Step 2: Implement the `CoderAgent`**
- Create the `CoderAgent` class.
- The most complex part will be the `run` method's interaction loop with the LLM. The prompt engineering is critical here. The system prompt must clearly define the available tools in a format the LLM can easily parse and use.
- The agent's logic will need to parse the LLM's response, identify the requested tool calls (e.g., in a JSON block), execute them using the `SandboxRunner` instance, and potentially send the results back to the LLM for the next turn.

**Step 3: Build the `LangGraph` Orchestrator**
- Create the `graph.py` module.
- Define the `CycleState` TypedDict.
- Implement the three node functions. The `_setup_sandbox_node` is particularly important, as it will create the `SandboxRunner` instance that gets passed through the rest of the graph via the state. It should use a `with` statement to ensure the sandbox is closed even if later nodes fail.
- Implement the `CoderWorkflow` class to assemble the nodes into a linear graph.

**Step 4: Integrate into the CLI**
- Create the `run_cycle` command in `ac_dd_core/cli.py`.
- This command will be responsible for finding and reading the `SPEC.md` for the given cycle ID.
- It will then create an instance of the `CoderWorkflow`, compile it, and invoke it with the initial state containing the spec content.
- It will use the `ConsolePresenter` to provide high-level status updates.

**Step 5: Write Comprehensive Tests**
- As this cycle introduces a major external dependency, the testing must be rigorous.
- Unit test the `CoderAgent` with a mocked `JulesClient` and a mocked `SandboxRunner` to verify its logic for parsing LLM responses and calling the correct tools.
- Create a dedicated, extensive integration test suite for the `SandboxRunner` itself. These tests will be marked as slow and will require a live `E2B_API_KEY`. They will test the entire lifecycle and all synchronization methods against a real E2B sandbox to guarantee that this critical component is working correctly.
- Create an end-to-end test for the `run-cycle` command. This test will mock the `JulesClient` but use the real `SandboxRunner`. It will verify that a simple code-generation task (e.g., creating a new file) is successfully completed, from the CLI command down to the file appearing on the local filesystem.

## 5. Test Strategy

The test strategy for Cycle 03 must be particularly rigorous due to the introduction of the stateful and remote E2B sandbox. The strategy will be heavily weighted towards integration testing to ensure the real-world behavior of this critical component is validated.

**Unit Testing Approach:**
- **`CoderAgent`:** The agent's logic will be tested in strict isolation. We will instantiate it with a mocked `JulesClient` and a mocked `SandboxRunner`. The key test will involve configuring the mocked `JulesClient` to return a canned response that contains a sequence of tool-use instructions (e.g., "First, `read_file('main.py')`, then `write_file('main.py', 'new_content')`"). The test will then assert that the `CoderAgent` correctly calls the `read_file` and `write_file` methods on the mocked `SandboxRunner` instance in the correct order and with the correct arguments. This validates the agent's response-parsing and tool-dispatching logic without the overhead of a real sandbox.
- **`LangGraph` Orchestrator:** The individual node functions of the graph will be unit-tested. For example, we can call the `_coder_agent_node` function directly with a sample `CycleState` containing a mocked `SandboxRunner`, and assert that it correctly invokes the mocked `CoderAgent` and updates the state as expected.

**Integration Testing Approach:**
- **`SandboxRunner` Service Integration Test:** This is the most important and comprehensive test of this cycle. It will be a dedicated test suite that interacts with a **real E2B sandbox** and will be marked as such (e.g., `@pytest.mark.e2e`). The test suite will cover the full lifecycle and all functionalities:
  1.  It will create a temporary local directory with a sample `src` folder containing a few files.
  2.  It will instantiate and start the `SandboxRunner`.
  3.  It will call `runner.sync_to_sandbox()` and then use `runner.list_files('/')` to assert that the files were correctly uploaded and extracted.
  4.  It will test each tool individually: `write_file` to create a new file, `read_file` to get its content back, and assert they match.
  5.  It will call `runner.sync_from_sandbox()` and assert that the new file created in the sandbox now exists in the local temporary directory.
  6.  Finally, it will ensure the `runner.close()` method successfully terminates the session. Passing this suite provides high confidence in the most critical and complex part of this cycle.
- **End-to-End Command Test (with Mocked LLM):** This test will validate the entire workflow orchestrated by the `run-cycle` command.
  1.  It will use the `CliRunner` to invoke the `run-cycle` command with a dummy cycle ID.
  2.  It will mock the `JulesClient`. The mock will be configured to return a simple, hardcoded response that instructs the `CoderAgent` to perform a single action, like creating a new file named `src/hello.py` with specific content.
  3.  Crucially, it will use the **real** `SandboxRunner` service, allowing the test to create a live E2B sandbox.
  4.  After the `CliRunner` has finished executing the command, the test will check the local filesystem.
  5.  It will assert that the file `src/hello.py` now exists and that its content matches what the mocked LLM response specified. This test proves that all the components—CLI, LangGraph, Agent, and the real SandboxRunner—are integrated correctly and can work together to accomplish the core task of the cycle.
