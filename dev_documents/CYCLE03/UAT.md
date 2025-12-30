# UAT.md - Cycle 03: Coder Agent and Sandbox Execution (`run-cycle` command)

## 1. Test Scenarios

This document provides the User Acceptance Testing (UAT) scenarios for Cycle 03. The core focus of this cycle is the `run-cycle` command and its ability to orchestrate the Coder Agent within the secure E2B sandbox to implement features. These tests are designed from the user's perspective to ensure that this complex, multi-stage workflow is reliable, robust, and performs its core function correctly: turning a specification into code on the user's local machine. The scenarios cover the "happy path" of creating and modifying code, as well as critical failure paths related to missing specifications or invalid cloud credentials.

| Scenario ID | Description                                                                 | Priority |
|-------------|-----------------------------------------------------------------------------|----------|
| UAT-03-001  | Successful Code Generation and Synchronization for a Brand-New File         | High     |
| UAT-03-02  | Successful Code Modification and Synchronization of an Existing File        | High     |
| UAT-03-03  | Command Fails Gracefully if the `SPEC.md` for the Cycle is Missing        | High     |
| UAT-03-04  | Command Fails Gracefully on an Invalid E2B API Key                          | High     |
| UAT-03-05  | Sandbox Environment is Guaranteed to be Clean and Ephemeral Between Runs    | Medium   |

**Scenario Details:**

**UAT-03-001: Successful Code Generation and Synchronization for a Brand-New File**
This is the most fundamental "happy path" test for this cycle. It validates the entire end-to-end workflow for a net-new feature. The test ensures the system can correctly provision a remote sandbox, sync the initial state of the user's project into it, allow the AI Coder Agent to create a new source code file from scratch based on a specification, and then successfully transfer this newly created file back to the user's local machine. The success of this scenario is a major milestone, as it proves that the core capability of the AC-CDD framework—turning a "contract" into tangible code—is fully functional. It validates the integration of the CLI, the orchestrator, the agent, and the sandbox service.

**UAT-03-02: Successful Code Modification and Synchronization of an Existing File**
This scenario tests a more common and arguably more complex real-world use case: refactoring or adding to existing code. The Coder Agent must demonstrate the ability to read an existing file's content, understand the context, and apply a targeted change as requested by the specification. This test is critical because it verifies that the agent's file system tools (`read_file`, `write_file`) are working correctly in concert. It also ensures that the final file synchronization process correctly updates the local file with the modifications, rather than causing data loss or corruption. This demonstrates a more sophisticated level of automated development beyond simple file creation.

**UAT-03-03: Command Fails Gracefully if the `SPEC.md` for the Cycle is Missing**
This scenario tests the system's robustness against a common user error. A user might try to run a cycle for which the architectural documents have not yet been generated, or which they have accidentally deleted. A well-designed system should anticipate this. This test ensures the `run-cycle` command first verifies the existence of the required `SPEC.md` "contract." If it is not found, the command must terminate immediately with a clear, helpful error message. This prevents the system from wasting time and resources spinning up a cloud sandbox for a task that is doomed to fail, and it provides a user-friendly experience by guiding the user on how to fix the problem.

**UAT-03-04: Command Fails Gracefully on an Invalid E2B API Key**
This scenario is critical for testing the system's resilience to external service failures, particularly misconfiguration. If the user has an incorrect or expired `E2B_API_KEY`, the system will be unable to provision the sandbox. This test verifies that the system can catch the resulting authentication or connection error from the `e2b` SDK and translate it into a simple, actionable error message for the user. Instead of showing a complex network-level stack trace, the system should point the user directly to the likely cause: their `.env` file configuration. This is essential for user trust and for making the system easy to debug.

**UAT-03-05: Sandbox Environment is Guaranteed to be Clean and Ephemeral Between Runs**
This scenario tests a core architectural promise of the AC-CDD framework: that the sandbox environments are ephemeral and isolated. This means that work done in one run should have no impact on a subsequent run. This test verifies this by running a cycle that creates a specific file, and then, after cleaning up the local state, running a different cycle. The test ensures that the second run starts in a fresh sandbox that only contains the current state of the local `src` directory, and does not contain any artifacts or modifications left over from the first run. This is a critical test for guaranteeing reproducibility and preventing the kind of "state pollution" that can lead to flaky and unreliable tests.

## 2. Behavior Definitions

**Scenario: UAT-03-001 - Successful Code Generation and Synchronization for a Brand-New File**

*   **GIVEN** I am a user with a valid `.env` file containing a working `JULES_API_KEY` and a working `E2B_API_KEY`.
*   **AND** I have a specification file at `dev_documents/CYCLE03/SPEC.md` that clearly instructs the Coder Agent to "create a new Python file named `hello.py` in the `src/` directory, and this file should contain a single line of code: `print('Hello, World!')`".
*   **AND** my local `src/` directory does not currently contain a file named `hello.py`.
*   **WHEN** I execute the command `uv run manage.py run-cycle --id 03` in my terminal.
*   **THEN** the system should display a series of status messages, clearly indicating the major stages of the process: "Provisioning E2B sandbox...", "Running Coder Agent...", "Synchronizing results...".
*   **AND** the command should exit cleanly with a success message, such as "Cycle 03 completed successfully. Code has been updated in your local 'src' directory.".
*   **AND** a new file named `hello.py` must now exist in my local `src/` directory.
*   **AND** the content of this `src/hello.py` file must be exactly `print('Hello, World!')`.

**Scenario: UAT-03-02 - Successful Code Modification and Synchronization of an Existing File**

*   **GIVEN** I am a user with a valid `.env` file.
*   **AND** I have an existing file `src/app.py` on my local filesystem with the initial content: `def main():\n    # TODO: Implement\n    pass`.
*   **AND** the specification at `dev_documents/CYCLE03/SPEC.md` instructs the agent to "modify the `src/app.py` file to replace the '# TODO' comment with the code `print('Application running.')`".
*   **WHEN** I execute the command `uv run manage.py run-cycle --id 03`.
*   **THEN** the command should complete successfully.
*   **AND** the `src/app.py` file on my local filesystem should have been modified.
*   **AND** its new content should be exactly: `def main():\n    print('Application running.')\n    pass`.

**Scenario: UAT-03-03 - Command Fails Gracefully if the `SPEC.md` for the Cycle is Missing**

*   **GIVEN** I am a user with a valid `.env` file.
*   **AND** the specification file `dev_documents/CYCLE04/SPEC.md` does not exist.
*   **WHEN** I attempt to run the cycle by executing `uv run manage.py run-cycle --id 04`.
*   **THEN** the system should immediately fail, before it attempts to create a sandbox.
*   **AND** a clear error message must be displayed in the console, such as "Error: Cannot start cycle. The specification file 'dev_documents/CYCLE04/SPEC.md' was not found. Please run the 'gen-cycles' command first.".
*   **AND** the command must terminate with a non-zero exit code.
*   **AND** my local `src/` directory must not have been modified in any way.

**Scenario: UAT-03-04 - Command Fails Gracefully on an Invalid E2B API Key**

*   **GIVEN** I have a valid `dev_documents/CYCLE03/SPEC.md` file ready to be executed.
*   **AND** the `E2B_API_KEY` in my `.env` file is invalid, mistyped, or has been revoked.
*   **WHEN** I execute the command `uv run manage.py run-cycle --id 03`.
*   **THEN** the system should attempt to provision the sandbox and fail at this stage.
*   **AND** it must display a specific, user-friendly error message, such as "Error: Failed to create secure sandbox. Please check that your E2B_API_KEY in the .env file is correct and has not expired.".
*   **AND** the command must terminate with a non-zero exit code.

**Scenario: UAT-03-05 - Sandbox Environment is Guaranteed to be Clean and Ephemeral Between Runs**

*   **GIVEN** I am a user with a valid `.env` file.
*   **AND** my local `src/` directory is currently empty.
*   **AND** the specification for Cycle 01 (`SPEC.md`) instructs the agent to create a single file named `src/cycle_one_output.txt`.
*   **WHEN** I execute `uv run manage.py run-cycle --id 01`.
*   **THEN** the command completes, and the file `src/cycle_one_output.txt` is now on my local filesystem.
*   **AND** I then delete this file locally, so my `src/` directory is empty again.
*   **AND** the specification for Cycle 02 (`SPEC.md`) instructs the agent to create a different file named `src/cycle_two_output.txt`.
*   **WHEN** I immediately execute `uv run manage.py run-cycle --id 02`.
*   **THEN** the command completes successfully.
*   **AND** my local `src/` directory must contain the file `src/cycle_two_output.txt`.
*   **AND** my local `src/` directory must **NOT** contain the file `src/cycle_one_output.txt`, proving that the second run started in a new, clean sandbox.
