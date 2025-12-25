# Cycle 05: Finalisation - User Acceptance Test (UAT) Document

**Version:** 1.0.0
**Status:** Final
**Cycle:** 05
**Title:** UAT for User Interface, Optimisation, and Packaging

## 1. Test Scenarios

This document outlines the User Acceptance Tests (UAT) for the final development cycle. The focus is on the user experience, installation, and documentation of the finished MLIP-AutoPipe tool. These tests are designed to be performed by an end-user to ensure the software is not only functional but also easy to install, use, and understand.

| Scenario ID | Test Scenario Description                                                                                             | Priority |
| :---------- | :---------------------------------------------------------------------------------------------------------------------- | :------- |
| UAT-C05-01  | **Successful Installation via Pip:** Verify that the tool can be easily installed from a package file using `pip`.        | High     |
| UAT-C05-02  | **Basic CLI Execution:** Confirm that the main `mlip-pipe run` command successfully launches the workflow.               | High     |
| UAT-C05-03  | **Verbose Output Control:** Check that the `--verbose` flag provides more detailed logging output for debugging.           | Medium   |
| UAT-C05-04  | **Graceful Error Reporting:** Ensure that if the backend workflow fails, the CLI reports a clean error message and exits correctly. | High     |
| UAT-C05-05  | **Following the "Getting Started" Tutorial:** A new user must be able to follow the main documentation tutorial successfully. | High     |

### Scenario Details

**UAT-C05-01: Successful Installation via Pip**
This test validates the core distributability of the application. The user will be provided with the final package file (e.g., `mlip_autopipec-1.0.0-py3-none-any.whl`). In a clean Python virtual environment, they will run the command `pip install /path/to/package.whl`. The acceptance criteria are:
1. The `pip install` command must complete without any errors.
2. After installation, running the command `mlip-pipe --help` must display the main help menu for the application, confirming that the entry point was registered correctly.

**UAT-C05-02: Basic CLI Execution**
This test verifies the primary function of the new CLI. The user will create a simple `input.yaml` file for a known-working test case (like bulk Silicon). They will then execute the command `mlip-pipe run input.yaml`. The acceptance criterion is that the workflow runs to completion and exits successfully, producing the same final output (a trained model) as the previous script-based execution method. This ensures the CLI is correctly wired to the backend orchestrator.

**UAT-C05-03: Verbose Output Control**
This test confirms that the user can control the level of logging detail. The user will first run the command `mlip-pipe run input.yaml`. They will note the amount of console output. They will then run the same command again, but with the verbose flag: `mlip-pipe run --verbose input.yaml`. The acceptance criterion is that the second run produces significantly more detailed output, including DEBUG-level messages about the internal state of the modules, which would be useful for troubleshooting.

**UAT-C05-04: Graceful Error Reporting**
This test validates the user-friendliness of the error handling. The user will deliberately provoke an error (e.g., by providing an `input.yaml` that points to a non-existent element, as in UAT-C02-05). The acceptance criteria are:
1. The application must not crash with a long, intimidating Python traceback.
2. The CLI must print a single, clear, color-coded error message to the console (e.g., "ERROR: The element 'Zz' is not supported.").
3. The command must exit with a non-zero status code (which can be checked on Linux with `echo $?`).

**UAT-C05-05: Following the "Getting Started" Tutorial**
This is a holistic test of the user documentation. A user who was not involved in the development process will be given access to the generated documentation website. They will be asked to follow the "Getting Started" or "Tutorial" page from the beginning. The acceptance criterion is that the user can successfully install the software and run the example case to completion, achieving the documented result, without needing to ask the developers for clarification. This test validates the clarity, accuracy, and completeness of the user guide.

## 2. Behavior Definitions

The following behavior definitions are written in Gherkin style to provide a clear, unambiguous description of the expected system behavior for the key test scenarios.

---

**Scenario: UAT-C05-01 - Successful Installation via Pip**

**GIVEN** I am in a clean Python virtual environment.
**AND** I have the package file `mlip_autopipec-1.0.0-py3-none-any.whl`.
**WHEN** I run the command `pip install mlip_autopipec-1.0.0-py3-none-any.whl`.
**THEN** the command must finish with a "Successfully installed" message.
**AND** when I then run the command `mlip-pipe --help`, it must display a help message and not a "command not found" error.

---

**Scenario: UAT-C05-02 - Basic CLI Execution**

**GIVEN** the `mlip-pipe` tool is successfully installed.
**AND** I have a valid `input.yaml` file.
**WHEN** I run the command `mlip-pipe run input.yaml` from my terminal.
**THEN** the workflow should start and run to completion.
**AND** the command should exit with a status code of 0.
**AND** a final MLIP model file should be present in the output directory.

---

**Scenario: UAT-C05-03 - Verbose Output Control**

**GIVEN** the `mlip-pipe` tool is successfully installed.
**AND** I have a valid `input.yaml` file.
**WHEN** I run the command `mlip-pipe run --verbose input.yaml`.
**THEN** the console output should include detailed "DEBUG" messages throughout the process.
**WHEN** I run the same command without the `--verbose` flag.
**THEN** the console output should only contain "INFO" level messages and should be significantly shorter.

---

**Scenario: UAT-C05-04 - Graceful Error Reporting**

**GIVEN** the `mlip-pipe` tool is successfully installed.
**AND** I have an `input.yaml` file containing an invalid element name.
**WHEN** I run the command `mlip-pipe run input.yaml`.
**THEN** the command should not print a multi-line Python traceback.
**AND** a single, clear error message should be printed to the console in red text.
**AND** the command must exit with a status code other than 0.

---

**Scenario: UAT-C05-05 - Following the "Getting Started" Tutorial**

**GIVEN** I am a new user with access to the documentation website.
**WHEN** I follow the instructions on the "Tutorial" page step-by-step.
**THEN** I must be able to install the software successfully.
**AND** I must be able to run the provided example case without errors.
**AND** the final result I obtain should match the result described in the tutorial.

---
