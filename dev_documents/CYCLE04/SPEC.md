# SPEC.md - Cycle 04: Auditor and QA Agent Integration

## 1. Summary

This specification outlines the technical requirements for Cycle 04 of the Autonomous Development Environment (AC-CDD) project. This cycle represents a critical maturation of the system, evolving it from a pure code generation tool into a comprehensive development platform with an integrated quality assurance framework. Building directly upon the Coder Agent and sandbox execution capabilities established in Cycle 03, this cycle will introduce and integrate two new, specialized agents: the **QA Analyst Agent** and the **Auditor Agent**. The QA Analyst Agent's mission is to enforce functional correctness by automatically executing the project's test suite within the secure sandbox and rigorously verifying that the code behaves as defined in the `UAT.md` contract. Concurrently, the Auditor Agent will act as an automated code reviewer, performing a sophisticated static analysis of the generated code to identify a wide range of issues, including security vulnerabilities, performance bottlenecks, logical errors, and deviations from coding standards. The `run-cycle` command's `LangGraph` orchestrator will be significantly upgraded to incorporate new `TESTING` and `AUDITING` states, which will execute sequentially after the `CODING` phase. For this cycle, these agents will act as strict "quality gates." If any of these checks fail, the entire workflow will halt and provide a detailed report of the findings to the user. The capability for the system to automatically *fix* these reported issues is intentionally deferred to Cycle 05. The successful completion of Cycle 04 will mark a major milestone, transforming the `run-cycle` command into a powerful tool that not only writes code but also meticulously validates its correctness and quality against predefined standards, ensuring that only high-quality code is ever presented back to the user.

## 2. System Architecture

The architecture for Cycle 04 focuses on enriching the `LangGraph` orchestrator with more sophisticated logic and integrating two new agents that leverage the existing sandbox environment. The core change is the shift from a simple linear pipeline to a conditional one.

**1. LangGraph Orchestrator (Conditional Pipeline):**
The `LangGraph` workflow will be significantly extended to manage the new quality assurance stages. The sequence of states will now become a conditional pipeline: `SETUP_SANDBOX` -> `CODING` -> `TESTING` -> `AUDITING` -> `SYNC_BACK`. The key innovation lies in the edges connecting these states:
- **Edge from `TESTING`:** After the `TESTING` state completes, a conditional edge will evaluate the `TestResult` object. If the `passed` attribute is `True`, the graph will transition to the `AUDITING` state. If it is `False`, the graph will transition to a terminal `FAILURE` state. This `FAILURE` state will prevent further execution and will be responsible for reporting the detailed test failures to the user.
- **Edge from `AUDITING`:** Similarly, a conditional edge after the `AUDITING` state will inspect the `AuditReport`. If the report indicates that no critical issues were found, the graph will proceed to the `SYNC_BACK` state. If critical issues are present, it will transition to the `FAILURE` state, reporting the audit findings.
This conditional logic transforms the graph from a simple executor into a decision-making engine, which is the foundational concept of a quality gate.

**2. QA Analyst Agent:**
This new agent is a specialized component focused entirely on verifying the functional correctness of the code. Its operational context is the E2B sandbox, and its responsibilities are:
- To receive instructions on how to run the project's test suite (e.g., the command `pytest tests/`).
- To use the `SandboxRunner`'s `execute_command` capability to run this command within the sandbox.
- To meticulously capture all outputs from the test run: the exit code, the `stdout`, and the `stderr`.
- To parse this raw output into a structured `TestResult` data object. The primary logic here is simple but crucial: an exit code of `0` signifies success (`passed=True`), while any other exit code signifies failure (`passed=False`).
- To return this `TestResult` object to the `LangGraph` orchestrator, providing the necessary data for the conditional edge to make its routing decision.

**3. Auditor Agent:**
This agent acts as an automated, AI-powered senior code reviewer. It is responsible for enforcing non-functional requirements like code quality, security, and maintainability. Its workflow is as follows:
- It is triggered after the `TESTING` stage has successfully completed.
- It receives, via the graph's state, the list of files that were modified by the Coder Agent during the `CODING` phase.
- It uses the `SandboxRunner`'s `read_file` tool to fetch the latest content of these modified files from within the sandbox.
- It then uses a new `FastModelClient` service to send this code to a cost-effective, analytical LLM (e.g., Gemini Flash). The prompt will be carefully engineered to instruct the model to perform a comprehensive review, looking for specific categories of flaws.
- It parses the natural language response from the LLM into a structured `AuditReport` data object, which contains a list of `AuditIssue` objects.
- It returns this `AuditReport` to the `LangGraph`, which then uses it to decide whether to proceed or halt the workflow.

**4. Fast Model Client Service:**
To optimize for both speed and cost, the Auditor Agent will not use the same powerful (and expensive) Jules model as the Coder Agent. A new service, `FastModelClient`, will be introduced. This service will be a client for more efficient LLMs like Google's Gemini or Anthropic's Claude Haiku. Its architecture will be very similar to the `JulesClient`—it will handle authentication, request/response formatting, and error handling for a different API endpoint and with a different API key (e.g., `GEMINI_API_KEY`). This architectural choice allows the system to use the right tool (and cost profile) for the right job.

The overall data flow for the `run-cycle` command becomes significantly more sophisticated. The process begins as in Cycle 03. After the `CODING` node, the `TESTING` node is invoked, and the QA Analyst Agent runs the tests. If they pass, the graph proceeds to the `AUDITING` node, where the Auditor Agent fetches the code and sends it for review. Only if this audit also passes does the graph finally proceed to the `SYNC_BACK` node. If either gate fails, the process is aborted.

## 3. Design Architecture

The design for Cycle 04 will focus on creating the two new agents, defining the data structures for their reports, and, most importantly, implementing the conditional logic within the `LangGraph`.

**1. File and Directory Structure:**
- `dev_src/ac_dd_core/`:
  - `agents/qa_analyst.py`: A new module for the `QAAnalystAgent` class.
  - `agents/auditor.py`: A new module for the `AuditorAgent` class.
  - `services/fast_model.py`: A new module for the `FastModelClient` class.
  - `graph.py`: The `CoderWorkflow` class within this module will be substantially updated to include the new nodes and conditional edges.
  - `domain_models.py`: A new module to house the shared Pydantic data models (`TestResult`, `AuditReport`, etc.) to ensure type safety and a clear data contract between the components.

**2. Key Classes and Functions:**
- **`ac_dd_core.graph.py`:**
  - `CoderWorkflow`:
    - `_testing_node(self, state: CycleState) -> CycleState`: A new node function. It will instantiate the `QAAnalystAgent`, invoke its `run_tests` method, and then update the `state` dictionary with the returned `TestResult` object.
    - `_auditing_node(self, state: CycleState) -> CycleState`: A new node function. It will instantiate the `AuditorAgent`, call its `run_audit` method (passing the list of modified files from the state), and update the state with the resulting `AuditReport`.
    - `_decide_after_testing(self, state: CycleState) -> str`: A new function that will be used to implement the conditional edge. It will inspect `state['test_result'].passed` and return the string name of the next node to transition to, either `"auditing"` or `"failure"`.
    - `_decide_after_auditing(self, state: CycleState) -> str`: A similar conditional edge function that inspects the `AuditReport` in the state.
    - The `build_graph` method will be rewritten to register these new nodes and to add the conditional edges using the `graph.add_conditional_edges()` method.
- **`ac_dd_core.agents.qa_analyst.py`:**
  - `class QAAnalystAgent:`
    - `__init__(self, sandbox: SandboxRunner)`: The constructor takes an active sandbox instance.
    - `run_tests(self, test_command: str = "pytest") -> TestResult`: The main method. It will call `self.sandbox.execute_command(test_command)`, await its result, and then construct and return a `TestResult` Pydantic model based on the exit code, stdout, and stderr.
- **`ac_dd_core.agents.auditor.py`:**
  - `class AuditorAgent:`
    - `__init__(self, sandbox: SandboxRunner, client: FastModelClient)`: Constructor with dependencies.
    - `run_audit(self, modified_files: List[str]) -> AuditReport`: The main method. It will loop through the `modified_files`, read their content using the `sandbox`, assemble a comprehensive prompt for the `FastModelClient`, and then call the client. A key part of this method will be a call to a private helper, `_parse_audit_response`, to transform the LLM's raw text response into the structured `AuditReport` model.
- **`ac_dd_core.services.fast_model.py`:**
  - `class FastModelClient:`:
    - `__init__(self, api_key: SecretStr, model_name: str)`: Constructor.
    - `review_code(self, code_prompt: str) -> str`: This method will be responsible for the specifics of interacting with the chosen "fast model" API (e.g., Gemini). It will handle the unique authentication scheme, request payload structure, and response format of that specific API.
- **`ac_dd_core.domain_models.py`:**
  - `class TestResult(BaseModel):`: Will contain fields like `passed: bool`, `stdout: str`, `stderr: str`.
  - `class AuditIssue(BaseModel):`: Will define the structure of a single issue, with fields like `file_path: str`, `line_number: int`, `description: str`, and `severity: Literal['Critical', 'Major', 'Minor']`.
  - `class AuditReport(BaseModel):`: Will contain `issues_found: bool` and `issues: List[AuditIssue]`.

This design promotes a highly structured and reliable workflow. By using strongly-typed Pydantic models as the data carriers between states, we eliminate the need for fragile string parsing within the orchestration logic itself, making the graph's decision-making process much more robust.

## 4. Implementation Approach

The implementation will proceed by building the new, independent components first (clients, models, agents) and then integrating them into the `LangGraph`.

**Step 1: Define the Domain Models**
- Create the `ac_dd_core/domain_models.py` file.
- Implement the `TestResult`, `AuditIssue`, and `AuditReport` Pydantic models. This is the first step as it defines the "contract" for the data that will be passed between the new components.

**Step 2: Implement the `FastModelClient`**
- Create the `FastModelClient` class in `ac_dd_core/services/fast_model.py`.
- The implementation will be similar to the `JulesClient`, using `httpx` and handling API-specific details. The configuration in `settings` will need to be updated to manage the new API keys.

**Step 3: Implement the `QAAnalystAgent`**
- Create the `QAAnalystAgent` class.
- Its implementation will be straightforward, primarily acting as a wrapper around the `sandbox.execute_command` method and then populating the `TestResult` model from the command's output.

**Step 4: Implement the `AuditorAgent`**
- Create the `AuditorAgent` class.
- The `run_audit` method will require careful prompt engineering to instruct the LLM on its role and expected output format.
- The most complex part of this agent will be the `_parse_audit_response` helper method. This method will need to robustly parse the LLM's natural language response (which might be in Markdown, JSON, or another format) and reliably convert it into a list of `AuditIssue` objects.

**Step 5: Extend the `LangGraph`**
- This is the most critical integration step. In `ac_dd_core/graph.py`:
- Add the new node functions (`_testing_node`, `_auditing_node`) and the conditional edge functions (`_decide_after_testing`, `_decide_after_auditing`).
- In the `build_graph` method, add the new nodes.
- Remove the direct edge from `CODING` to `SYNC_BACK`.
- Add a new edge from `CODING` to `TESTING`.
- Use the `graph.add_conditional_edges` method to wire up the `TESTING` node to the `_decide_after_testing` function, which will then branch to either the `AUDITING` node or a new `FAILURE` node.
- Do the same for the `AUDITING` node, branching to either `SYNC_BACK` or `FAILURE`.

**Step 6: Update CLI and Configuration**
- The global `settings` object in `config.py` will be updated to load the new API keys (e.g., `GEMINI_API_KEY`) and potentially the model names for the auditor.
- The `run_cycle` command in `cli.py` itself should require minimal changes, as all the new complexity is encapsulated within the `CoderWorkflow` graph.

## 5. Test Strategy

The testing for Cycle 04 will be heavily focused on verifying the correctness of the new conditional logic in the `LangGraph` and ensuring the new agents produce their reports in the expected format.

**Unit Testing Approach:**
- **`QAAnalystAgent`:** This agent's `run_tests` method will be tested by providing it with a mocked `SandboxRunner`. We will configure the mock's `execute_command` method to return different `ProcessOutput` objects. For example, one test will simulate a successful test run (exit code 0), and we'll assert that the agent returns a `TestResult` with `passed=True`. Another test will simulate a failure (non-zero exit code) with specific error text in `stderr`, and we'll assert that the `TestResult` shows `passed=False` and that the `stderr` string was correctly captured.
- **`AuditorAgent`:** This agent will be tested with a mocked `SandboxRunner` (to provide sample code) and a mocked `FastModelClient`. We will configure the mock client to return a canned string representing a typical audit review. The test will then assert that the agent's `_parse_audit_response` logic correctly and robustly parses this string into the expected `AuditReport` Pydantic model.
- **`LangGraph` Conditional Logic:** The decision functions (e.g., `_decide_after_testing`) will be unit-tested directly. We will create sample `CycleState` objects manually—one containing a passing `TestResult`, another containing a failing one. We will then call the decision function with each of these states and assert that it returns the correct string name for the next node (e.g., `"auditing"` or `"failure"`). This verifies the core routing logic in isolation.

**Integration Testing Approach:**
- **Full Graph Flow Simulation:** The primary integration test will validate the new conditional workflow of the `LangGraph`. We will achieve this by mocking the agents themselves at the node level.
  1. We will invoke the full `CoderWorkflow` graph.
  2. The `_coder_agent_node` will be mocked to simply return a list of dummy file paths.
  3. The `_testing_node` will be mocked to return a hardcoded `TestResult` object. In one test run, this will be a "passing" object. In another, it will be a "failing" object.
  4. We will assert that when the "failing" `TestResult` is injected, the graph terminates early and does not execute the audit node.
  5. We will then run a test with a "passing" `TestResult` but a "failing" `AuditReport` (also injected via a mock). We will assert that the graph executes the testing and auditing nodes but not the final sync node. This test suite verifies the graph's high-level control flow is correct.
- **End-to-End Command Test (with Mocked LLMs):** This test will validate the `run-cycle` command with the new quality gates.
  1. It will be invoked via the `CliRunner`. It will use a **real E2B sandbox** but **mocked LLM clients**.
  2. **Failure Scenario:** We will configure the test runner inside the sandbox to fail (e.g., by having the mocked Coder Agent produce code that fails a unit test). We will assert that the `run-cycle` command terminates with a non-zero exit code, that the console output contains the test failure report from the sandbox, and that the local `src/` files have **not** been updated.
  3. **Success Scenario:** We will configure the mocked agents to produce code that passes both the (real) tests in the sandbox and the (mocked) audit. We will assert that the command completes successfully and that the local `src/` files **are** updated.
