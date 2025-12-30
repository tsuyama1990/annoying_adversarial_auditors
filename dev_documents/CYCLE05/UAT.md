# UAT.md - Cycle 05: Iterative Fixing and Full Orchestration

## 1. Test Scenarios

This document outlines the User Acceptance Testing (UAT) scenarios for Cycle 05. This final cycle focuses on the system's ultimate goal: achieving true, hands-off autonomy. The tests are designed to validate the "self-healing" capability, where the system can iteratively fix its own mistakes, and to ensure that this entire process is seamlessly integrated with standard Git-based version control workflows. These scenarios represent the culmination of all the project's features working in concert.

| Scenario ID | Description                                                              | Priority |
|-------------|--------------------------------------------------------------------------|----------|
| UAT-05-001  | Successful Self-Healing: Code Fails Tests, is Automatically Fixed, then Passes | High     |
| UAT-05-002  | Successful Self-Healing: Code Fails Audit, is Automatically Fixed, then Passes | High     |
| UAT-05-003  | Workflow Fails Gracefully after Maximum Iteration Limit is Reached       | High     |
| UAT-05-004  | A Successful Run Correctly Creates a Git Feature Branch and a Final Commit | High     |

**Scenario Details:**

**UAT-05-001: Successful Self-Healing: Code Fails Tests, is Automatically Fixed, then Passes**
This is the most critical and impressive scenario for the entire AC-CDD project. It is the ultimate demonstration of the system's autonomous capabilities. This test validates the entire feedback loop for functional regressions. The system must prove its ability to recognize that the code it generated has a bug (via a failing test), analyze the failure report, formulate a correction, apply the fix, and then re-validate the new code until it passes. This is the core "magic" of the self-healing workflow. Its success proves that the system is not just a code generator but an autonomous problem-solver, capable of overcoming the initial imperfections of AI-generated code.

**UAT-05-002: Successful Self-Healing: Code Fails Audit, is Automatically Fixed, then Passes**
This scenario complements the first by focusing on non-functional requirements. It's crucial that the system can self-correct not just for bugs, but also for quality and security issues. This test ensures that if the Auditor Agent flags a critical vulnerability or a major style violation, the system can use that feedback to loop back and have the Coder Agent produce a better, safer, or more compliant version of the code. This demonstrates a mature level of automation, where the definition of "correctness" extends beyond simple test-passing to encompass the broader principles of high-quality software engineering.

**UAT-05-003: Workflow Fails Gracefully after Maximum Iteration Limit is Reached**
This scenario tests a vital safety feature of the autonomous system. While we want the system to be persistent, we must also prevent it from running indefinitely if it encounters a problem it cannot solve. This test verifies that the `iteration_limit` is correctly enforced. If the Coder Agent repeatedly fails to fix a bug or an audit issue, the workflow must terminate after the specified number of attempts. The system must then provide a clear failure message to the user, indicating that it was unable to resolve the issue. This is a critical safeguard against runaway processes, wasted computational resources, and endless loops, ensuring that the system will always terminate and report a definitive outcome.

**UAT-05-04: A Successful Run Correctly Creates a Git Feature Branch and a Final Commit**
This scenario validates the system's integration with the foundational tools of modern software development, namely Git. It ensures that the autonomous workflow is not just a black box that modifies local files, but a well-behaved citizen in a version-controlled environment. This test verifies two key actions: first, that the `run-cycle` command automatically creates a new, appropriately named feature branch before starting its work, thereby isolating the AI's changes. Second, it verifies that only after the code has successfully passed all the iterative quality checks is it then committed to that branch with a clean, descriptive commit message. This ensures that the main branch remains protected and that the project's Git history accurately reflects the addition of a completed, validated feature.

## 2. Behavior Definitions

**Scenario: UAT-05-001 - Successful Self-Healing: Code Fails Tests, is Automatically Fixed, then Passes**

*   **GIVEN** I am a user on the `main` git branch with a valid setup.
*   **AND** my `SPEC.md` for Cycle 5 requires a Python function `divide(a, b)` that should handle division by zero by returning `None`.
*   **AND** the Coder Agent is configured to first generate a buggy implementation that does not handle division by zero (i.e., `return a / b`).
*   **AND** the project's test suite includes a test `test_divide_by_zero` that asserts `divide(10, 0) is None`.
*   **WHEN** I execute the `run-cycle --id 05` command.
*   **THEN** the console output should show the system entering the `TESTING` phase for iteration 1 and report that tests have failed.
*   **AND** the system should then display a message indicating a fixing attempt is starting, such as "Test failure detected. Starting fixing attempt 2 of 3."
*   **AND** the workflow should loop back to the `CODING` phase, where the agent generates a corrected implementation (e.g., `if b == 0: return None; return a / b`).
*   **AND** the `TESTING` phase for iteration 2 should then report that all tests have passed.
*   **AND** the `AUDITING` phase should also pass.
*   **AND** the command should complete with a final success message.
*   **AND** the corrected, working version of the `divide` function should be present in my local `src/` directory and committed to the new feature branch.

**Scenario: UAT-05-002 - Successful Self-Healing: Code Fails Audit, is Automatically Fixed, then Passes**

*   **GIVEN** I am a user with a valid setup.
*   **AND** the Coder Agent is configured to generate code that passes all functional tests, but contains a blatant security issue (e.g., executing a shell command with `subprocess.run(..., shell=True)`).
*   **AND** the Auditor Agent is configured to flag `shell=True` as a critical security vulnerability.
*   **WHEN** I execute the `run-cycle` command.
*   **THEN** the console should show that the `TESTING` phase passed successfully in iteration 1.
*   **AND** the console should then show that the `AUDITING` phase failed.
*   **AND** the system should start a fixing attempt for iteration 2.
*   **AND** the Coder Agent should then generate a safer implementation (e.g., passing the command as a list: `subprocess.run([...], shell=False)`).
*   **AND** in iteration 2, both the `TESTING` and `AUDITING` phases should pass.
*   **AND** the command should complete successfully, and the final, secure code should be committed.

**Scenario: UAT-05-003 - Workflow Fails Gracefully after Maximum Iteration Limit is Reached**

*   **GIVEN** I am a user with a valid setup.
*   **AND** the Coder Agent is configured in such a way that it is consistently unable to fix a persistent test failure.
*   **AND** the system's maximum iteration limit is configured to 3.
*   **WHEN** I execute the `run-cycle` command.
*   **THEN** the console output should show the `TESTING` phase failing for iteration 1, iteration 2, and iteration 3.
*   **AND** after the third failure, the workflow should stop looping.
*   **AND** the system must display a clear and final error message, such as "Error: Maximum iteration limit (3) reached. The agent was unable to produce a satisfactory solution.".
*   **AND** the command must terminate with a non-zero exit code.
*   **AND** no commit should be made to the git branch. The user should be left on the feature branch with the final, uncommitted (and still broken) code for manual inspection.

**Scenario: UAT-05-004 - A Successful Run Correctly Creates a Git Feature Branch and a Final Commit**

*   **GIVEN** I am a user and my current git branch is `main`.
*   **AND** I execute a `run-cycle --id 05` command that completes successfully (potentially after several self-healing iterations).
*   **WHEN** the command exits with a final success message.
*   **THEN** my shell's current git branch should now be `feature/cycle-05`.
*   **AND** when I run `git status`, it should report that the working tree is clean.
*   **AND** when I run `git log -1`, it should show a newly created commit.
*   **AND** the commit message of that new commit should be well-formed and descriptive, such as "feat(cycle-05): Implement the division feature with zero-handling".
*   **AND** the files included in that commit should be only the final, working versions of the code that passed all the quality gates.
