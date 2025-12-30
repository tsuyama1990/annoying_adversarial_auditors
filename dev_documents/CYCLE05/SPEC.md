# SPEC.md - Cycle 05: Iterative Fixing and Full Orchestration

## 1. Summary

This specification document details the technical requirements for Cycle 05, the final and most sophisticated phase in the development of the Autonomous Development Environment (AC-CDD). This cycle's paramount objective is to achieve true operational autonomy by "closing the loop" on the development process. While Cycle 04 successfully established critical quality gates that could halt the workflow upon detecting failures, Cycle 05 will empower the system to **automatically correct** those failures. This will be accomplished by fundamentally re-architecting the `run-cycle` workflow from a linear pipeline into a robust, iterative, self-healing loop. When the QA Analyst Agent reports a test failure or the Auditor Agent flags a code quality issue, the `LangGraph` orchestrator will no longer terminate the process. Instead, it will intelligently route the workflow back to the `CODING` state, arming the Coder Agent with the detailed failure reports as new, high-priority context. The Coder Agent will then be tasked with analyzing the errors and generating a patch to fix the very code it previously wrote. This "code -> test -> fix" cycle will continue until the code successfully passes all quality gates or until a predefined maximum number of iterations is reached, a crucial safeguard to prevent infinite loops. Furthermore, this cycle will professionalize the entire workflow by integrating it with standard developer practices through a new `GitManager` service. The system will automatically create a dedicated feature branch at the beginning of a cycle and, upon successful completion of the iterative process, will commit the final, validated code with a descriptive message. This final cycle transforms the AC-CDD from a powerful assistant into a truly autonomous agent capable of delivering high-quality, fully tested code with minimal to no human intervention.

## 2. System Architecture

The core architectural evolution in Cycle 05 is the transformation of the `LangGraph` orchestrator from a conditional pipeline into a true cyclic graph, capable of iterative self-correction. The existing agents' roles are not fundamentally changed, but they are now placed within this more dynamic and powerful orchestration context.

**1. LangGraph Orchestrator (Iterative, Cyclic Model):**
The `LangGraph` becomes the centerpiece of the architecture in this cycle. Its structure is fundamentally changed to enable the feedback loop.
- **Cyclic Edges:** The conditional edges introduced in Cycle 04 will be re-wired. Previously, a failure in the `TESTING` or `AUDITING` state would lead to a terminal `FAILURE` node. Now, a failure will route the workflow back to the `CODING` state. This creates the core loop of the self-healing mechanism.
- **State Enrichment:** The `CycleState` object that is passed between nodes becomes even more critical. When a failure occurs, the state that is passed back to the `CODING` node will be explicitly enriched with the `TestResult` or `AuditReport` object that contains the details of the failure. This ensures the Coder Agent has the precise context it needs to formulate a fix.
- **Iteration Limiter:** To prevent the system from getting stuck in an infinite loop (e.g., if the Coder Agent is unable to fix a particularly tricky bug), a crucial safety mechanism will be introduced. The `CycleState` will now include an `iteration_count`. This counter will be incremented each time the loop returns to the `CODING` state. A new conditional edge at the very beginning of the loop will check this counter. If it exceeds a configurable maximum (e.g., 3 or 5 attempts), the graph will exit the loop and transition to the permanent `FAILURE` state, ensuring the process always terminates.

**2. Coder Agent (Enhanced "Fixer" Role):**
The Coder Agent's role is significantly enhanced. It must now be able to function not just as an initial implementer but also as an effective debugger and refactorer.
- **Context-Aware Prompting:** The agent's prompt will now be dynamically constructed based on the current `iteration_count`.
  - On the first iteration, it receives the `SPEC.md` and is given an "implement" instruction.
  - On subsequent iterations, its prompt is augmented. It receives the original `SPEC.md` for context, but it also receives the full text of the test failure logs or the audit report. The core instruction in the prompt changes from "implement this feature" to "your previous attempt failed; analyze the following error report and fix the code."
- This change does not require a new agent, but rather a more sophisticated prompt-engineering layer that adapts the agent's task based on the workflow's state.

**3. Git Manager Service:**
To ensure the output of the AC-CDD framework integrates seamlessly with standard software development best practices, a new `GitManager` service will be introduced. This service will be a high-level abstraction over the `git` command-line tool, insulating the rest of the application from the specifics of `subprocess` calls. Its role is to bookend the `LangGraph` workflow:
- **`create_feature_branch`:** Before the `LangGraph` is invoked, the CLI will use this service to create a new, clean feature branch for the work, named systematically (e.g., `feature/cycle-05`). This isolates the autonomous work from the main branch.
- **`commit_changes`:** After the `LangGraph` has successfully completed its entire iterative process, the CLI will use this service to stage all the changes made within the `src/` directory and create a single, clean commit on the feature branch. The commit message will be generated automatically to summarize the completed cycle. This ensures that only fully-vetted, high-quality code is ever committed to the repository.

The new end-to-end workflow is a robust, self-correcting loop, framed by professional Git practices:
1. The CLI uses `GitManager` to create the `feature/cycle-05` branch.
2. The `LangGraph` starts (`iteration_count=1`).
3. The Coder Agent produces buggy code.
4. The QA Agent runs tests, which fail. The `TestResult` is saved to the state.
5. The graph loops back to the Coder Agent (`iteration_count=2`), passing the `TestResult` as context.
6. The Coder Agent produces a fix.
7. The QA Agent runs tests, which now pass.
8. The Auditor Agent runs its review and finds a security issue. The `AuditReport` is saved to the state.
9. The graph loops back to the Coder Agent (`iteration_count=3`), passing the `AuditReport` as context.
10. The Coder Agent produces a final, secure version of the code.
11. The QA Agent and Auditor Agent both pass the code.
12. The graph completes successfully, and the code is synced back locally.
13. The CLI uses `GitManager` to commit the final, correct code to the feature branch.

## 3. Design Architecture

The design for Cycle 05 will focus on the significant modifications to the `LangGraph`'s control flow and the implementation of the new, stateless `GitManager` service.

**1. File and Directory Structure:**
- `dev_src/ac_dd_core/`:
  - `graph.py`: This module will see the most significant changes. The `CoderWorkflow` class will be re-architected to implement the feedback loop, the state will be expanded, and the edge logic will become more complex.
  - `services/git.py`: A new module will be created to house the `GitManager` class.
  - `agents/coder.py`: The `CoderAgent`'s prompt construction logic will be updated to handle the new "fixing" context.

**2. Key Classes and Functions:**
- **`ac_dd_core.graph.py`:**
  - `CycleState` (TypedDict): This data structure will be expanded to include `iteration_count: int`, `test_result: Optional[TestResult] = None`, and `audit_report: Optional[AuditReport] = None`. Using `Optional` is key, as these fields will only be populated on failure.
  - `CoderWorkflow`:
    - The `build_graph` method will be heavily modified. The conditional edges from `_decide_after_testing` and `_decide_after_auditing` will now have their "failure" path point back to the `_coder_agent_node` instead of the `_failure_node`.
    - A new entry-point node for the loop, `_check_iteration_limit`, will be added. The main graph entry will point here. This node's conditional edge will check `state['iteration_count']` against a `MAX_ITERATIONS` constant. If the limit is exceeded, it will route to `_failure_node`; otherwise, it will route to `_coder_agent_node`.
    - The `_coder_agent_node` will now be responsible for incrementing its own `iteration_count` within the state each time it is called.
- **`ac_dd_core.agents/coder.py`:**
  - `class CoderAgent`:
    - The `run` method's signature will change to accept the full `CycleState` object so it can access the iteration count and failure reports.
    - A private `_build_prompt` method will be implemented. This method will contain the core logic for dynamically constructing the prompt. It will check `state.get('iteration_count', 1)`. If it's 1, it builds the standard "implement" prompt. If it's greater than 1, it will check for the presence of a `test_result` or `audit_report` in the state and dynamically build a "fix" prompt, carefully formatting the error logs and audit issues into the prompt text to give the LLM maximum context.
- **`dev_src/ac_dd_core/services/git.py`:**
  - `class GitManager:`
    - `__init__(self, repo_root: Path)`: The constructor will take the root path of the repository to ensure commands are run in the correct directory.
    - `create_feature_branch(self, cycle_id: str) -> None`: This method will execute `git checkout -b feature/cycle-{cycle_id}` using `subprocess.run`. It will include error handling to gracefully manage the case where the branch may already exist.
    - `commit_changes(self, file_paths: List[Path], commit_message: str) -> None`: This method will first execute `git add path1 path2 ...` for the list of modified files, followed by `git commit -m "..."`. It will raise a custom `GitError` exception if any of the underlying `subprocess` calls fail.
- **`ac_dd_core/cli.py`:**
  - The `run_cycle` command function will be updated to become the master orchestrator of the entire process. It will instantiate the `GitManager`. It will then wrap the entire `LangGraph` execution in a `try...except` block.
    - Before the `try`, it will call `git_manager.create_feature_branch(...)`.
    - Inside the `try`, it will invoke the graph.
    - If the graph execution is successful, it will proceed to call `git_manager.commit_changes(...)`.
    - If the graph fails (e.g., by hitting the iteration limit), the `except` block will catch the error, and the commit step will be skipped, leaving the user on the feature branch with the uncommitted, failed code for inspection.

## 4. Implementation Approach

The implementation will focus on the most significant architectural change first: modifying the `LangGraph` to support iteration.

**Step 1: Re-architect the `LangGraph` for Looping**
- In `ac_dd_core/graph.py`, begin by updating the `CycleState` TypedDict to include the new fields for iteration counting and optional error reports.
- Implement the `_check_iteration_limit` node and its conditional logic. This is the new entry point to the main execution loop.
- Modify the existing conditional decision functions (`_decide_after_testing`, etc.). Change the "failure" return value from `"failure"` to `"coder"`, effectively redirecting the flow back to the Coder Agent.
- Update the `build_graph` method to reflect this new cyclic structure. This will be the most complex part of the implementation.

**Step 2: Upgrade the `CoderAgent` for a "Fixer" Role**
- In `ac_dd_core/agents/coder.py`, refactor the `run` method to take the entire `CycleState`.
- Implement the `_build_prompt` helper method. This method will contain the `if/else` logic to create either an "implement" or a "fix" prompt. Pay close attention to formatting the error reports within the prompt to make them as clear as possible for the LLM.

**Step 3: Implement the `GitManager` Service**
- Create the `GitManager` class in the new `services/git.py` module.
- Implement its methods using Python's `subprocess.run`. Ensure that `check=True` is used to automatically raise an exception if a git command fails, and wrap these calls in `try...except` blocks to re-raise them as custom, more informative `GitError` exceptions.

**Step 4: Integrate Git Operations into the CLI Layer**
- In `ac_dd_core/cli.py`, modify the `run_cycle` function to include the calls to the `GitManager` at the beginning and end of the process, as described in the design section. This step elevates the `run_cycle` command from a simple script runner to a manager of a complete, version-controlled workflow.

**Step 5: Write Comprehensive Tests**
- The testing for this cycle is paramount.
- Write unit tests for the `GitManager`, mocking `subprocess.run` to ensure the correct git commands are being generated.
- Write specific unit tests for the `CoderAgent`'s new `_build_prompt` logic to verify that it correctly assembles both "implement" and "fix" prompts.
- Write unit tests for the `LangGraph`'s looping logic. For example, create a test where the mocked testing node *always* returns a failure, and assert that the graph executes the coding/testing loop exactly `MAX_ITERATIONS` times before finally failing.
- Create the capstone end-to-end integration test as described in the Test Strategy section. This test will be the ultimate validation of the entire system's functionality.

## 5. Test Strategy

The test strategy for Cycle 05 is the most comprehensive, focusing on validating the new iterative workflow and the critical Git integration.

**Unit Testing Approach:**
- **`GitManager`:** This service will be tested in isolation by mocking `subprocess.run`. For `create_feature_branch`, we will assert that `subprocess.run` is called with `['git', 'checkout', '-b', 'feature/cycle-05']`. For `commit_changes`, we will assert that it's called first with `['git', 'add', ...]` and then with `['git', 'commit', ...]`. We will also simulate a non-zero exit code from the mock and assert that our custom `GitError` is raised.
- **`CoderAgent` Prompt Logic:** The new dynamic prompt generation in the `CoderAgent` will have dedicated unit tests. We will call the internal `_build_prompt` method with various `CycleState` configurations. One test will pass a state with `iteration_count=1` and assert the prompt is the standard implementation prompt. Another will pass a state with `iteration_count=2` and a populated `TestResult` object, and we will assert that the resulting prompt string correctly includes the formatted error logs from the `TestResult`.
- **`LangGraph` Loop and Termination Logic:** The graph's control flow will be unit-tested. We will create a version of the graph where the agent nodes are replaced by simple mocks. In one test, we'll configure the mock testing node to always return a failing result. We will then run the graph and assert that the coding/testing loop is executed exactly `MAX_ITERATIONS` times and that the graph's final output state is "failure." This provides high confidence in the iteration limit safety mechanism.

**Integration Testing Approach:**
- **End-to-End Self-Healing Workflow with Git Integration (Capstone Test):** This single, comprehensive E2E test will serve as the ultimate validation for the entire project. It will be a complex test that simulates a real user workflow from beginning to end.
  1.  The test setup will programmatically create a new temporary directory and initialize a `git` repository within it.
  2.  The `run-cycle` command will be invoked using `CliRunner`.
  3.  All LLM clients (`JulesClient`, `FastModelClient`) will be mocked to control the agent's behavior.
  4.  The test will orchestrate a multi-iteration scenario:
      a. On the first call, the mocked `JulesClient` will return code with a deliberate, simple bug.
      b. The test will use a **real E2B sandbox** to run the actual test suite, which will fail.
      c. The test will assert that the workflow loops back. The `JulesClient` mock will be configured for its second call.
      d. On the second call, the mock will return the corrected code.
      e. The tests will be run again in the sandbox and will pass.
      f. The mocked `AuditorAgent` will return a passing report.
  5.  The `run-cycle` command should now complete successfully.
  6.  **Final Verification:** The test will then use `subprocess.run` to execute `git` commands against the temporary repository to verify the final state. It will assert that:
      a. The current branch is now `feature/cycle-...`.
      b. A new commit exists on this branch.
      c. When the repository is checked out to this new commit, the files in the `src/` directory contain the **final, corrected** version of the code.
Passing this test provides extremely high confidence that the entire system, from Git integration to the self-healing loop to the sandbox execution, is working as designed.
