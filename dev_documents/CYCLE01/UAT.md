# UAT.md - Cycle 01: Core CLI, Initialization, and Configuration

## 1. Test Scenarios

This document outlines the User Acceptance Testing (UAT) scenarios for Cycle 01. The primary focus of this cycle is the `init` command, which represents the user's critical first interaction with the Autonomous Development Environment (AC-CDD). The success of this initial experience is paramount for user trust and adoption. These test scenarios are therefore designed to be comprehensive, ensuring that the initialization process is not only functional on the "happy path" but is also robust, user-friendly, and provides clear, actionable feedback in cases of error or misconfiguration. The tests will validate all aspects of the command, from its environmental prerequisite checks to its interactive secret-gathering process and its handling of existing configuration files.

| Scenario ID | Description                                                              | Priority |
|-------------|--------------------------------------------------------------------------|----------|
| UAT-01-001  | Successful Initialization on a Clean Environment                         | High     |
| UAT-01-002  | Initialization Fails Due to Missing `git` Prerequisite                   | High     |
| UAT-01-003  | Handling of a Pre-existing `.env` File with User Confirmation            | Medium   |
| UAT-01-004  | Handling of a Pre-existing `.env` File with User Rejection               | Medium   |
| UAT-01-005  | System Re-prompts for a Required API Key if User Provides Empty Input    | High     |
| UAT-01-006  | Initialization Fails Due to Missing `gh` Prerequisite                    | High     |
| UAT-01-007  | Initialization Fails Due to Missing `uv` Prerequisite                    | High     |

**Scenario Details:**

**UAT-01-001: Successful Initialization on a Clean Environment**
This is the most critical scenario and represents the ideal user journey. It validates the primary function of the `init` command from end to end. The test ensures that a user who has correctly set up their system with the required tools can run the `init` command and, through an interactive process, successfully generate a complete and syntactically correct `.env` file. A successful outcome of this test signifies that the core value proposition of the `init` command—to make environment setup simple and reliable—is met. It is the foundation upon which all subsequent user actions depend.

**UAT-01-002, UAT-01-006, UAT-01-007: Initialization Fails Due to Missing Prerequisites**
These scenarios are crucial for ensuring a positive user experience in the face of environmental issues. The system must be robust enough to detect when a required dependency (`git`, `gh`, or `uv`) is not available. More importantly, it must fail gracefully. Instead of crashing or producing a cryptic error, the system must provide a clear, concise, and helpful error message that explicitly names the missing tool and advises the user on how to resolve the issue. This demonstrates that the system is designed with the user in mind, anticipating common setup problems and providing direct guidance, which prevents user frustration and reduces the need for support.

**UAT-01-003 & UAT-01-004: Handling of a Pre-existing `.env` File**
These scenarios test the system's respect for the user's existing work and configuration. It is common for a user to re-run an initialization command. This test ensures that the system does not perform a destructive action (overwriting an existing `.env` file) without explicit user consent. By prompting the user with a clear "yes/no" choice, the system prevents the accidental deletion of potentially important secrets. UAT-01-003 validates the "yes" path, ensuring the overwrite proceeds as expected. UAT-01-004 validates the "no" path, ensuring the command aborts cleanly without making any changes, which is the safe default.

**UAT-01-005: System Re-prompts for a Required API Key if User Provides Empty Input**
This scenario tests the input validation robustness of the interactive setup. Users often make mistakes, such as accidentally hitting Enter before typing a value. This test ensures that the system is designed defensively. For required fields like API keys, an empty input is invalid. The test verifies that the system detects this, provides an informative message (e.g., "This field cannot be empty."), and re-prompts the user for the correct input, rather than proceeding and creating an invalid `.env` file that would cause failures later. This makes the initialization process more resilient to common user errors.

## 2. Behavior Definitions

**Scenario: UAT-01-001 - Successful Initialization on a Clean Environment**

*   **GIVEN** I am a new user of the AC-CDD tool who has just cloned the repository.
*   **AND** my system has `git`, `gh` (GitHub CLI), and `uv` installed and correctly configured in the system's PATH.
*   **AND** I do not have a file named `.env` in the root directory of the project.
*   **WHEN** I execute the command `uv run manage.py init` from the project's root directory.
*   **THEN** the system should first verify that all prerequisites are met without displaying any error.
*   **AND** the system should then begin an interactive session, prompting me for each required API key, one by one, as defined in the `.env.example` template.
*   **AND** when prompted for `JULES_API_KEY`, I enter the value `my_secret_jules_key`.
*   **AND** when prompted for `E2B_API_KEY`, I enter the value `my_secret_e2b_key`.
*   **AND** I provide valid, non-empty values for all other prompts.
*   **THEN** after the last prompt, the system should display a clear and positive success message, such as "Configuration successful! Your .env file has been created.".
*   **AND** a new file named `.env` must be present in the project's root directory.
*   **AND** upon inspecting the `.env` file, it must contain the exact line `JULES_API_KEY=my_secret_jules_key`.
*   **AND** it must also contain the exact line `E2B_API_KEY=my_secret_e2b_key`.

**Scenario: UAT-01-002 - Initialization Fails Due to Missing `git` Prerequisite**

*   **GIVEN** I am a new user of the AC-CDD tool.
*   **AND** the `git` command-line tool is not installed on my system, or it is not available in the shell's PATH.
*   **WHEN** I execute the command `uv run manage.py init`.
*   **THEN** the system should immediately display a clear and specific error message, such as "Error: Prerequisite 'git' could not be found. Please install Git and ensure it is available in your system's PATH.".
*   **AND** the command should terminate its execution at this point.
*   **AND** it should return a non-zero exit code to the shell to indicate failure.
*   **AND** no `.env` file should be created, and no prompts for API keys should be displayed.

**Scenario: UAT-01-003 - Handling of a Pre-existing `.env` File with User Confirmation**

*   **GIVEN** I am a user who has previously configured the environment.
*   **AND** a file named `.env` already exists in my project root, containing the line `JULES_API_KEY=old_key`.
*   **WHEN** I execute the command `uv run manage.py init` for a second time.
*   **THEN** the system should detect the existing file and prompt me with a clear, explicit warning and a choice, such as "A .env file already exists. Overwriting will delete your current settings. Do you want to continue? [y/N]: ".
*   **AND** I type `y` and press Enter.
*   **THEN** the system should proceed with the interactive prompting session as in the successful initialization scenario.
*   **AND** when prompted for `JULES_API_KEY`, I enter the value `new_key`.
*   **THEN** the command should complete successfully.
*   **AND** the `.env` file in the project root should be updated to contain the line `JULES_API_KEY=new_key`, and the old value should be gone.

**Scenario: UAT-01-004 - Handling of a Pre-existing `.env` File with User Rejection**

*   **GIVEN** I am a user with a pre-existing `.env` file containing `JULES_API_KEY=my_preserved_key`.
*   **WHEN** I execute `uv run manage.py init`.
*   **THEN** the system prompts me with the overwrite warning: "A .env file already exists. Overwriting will delete your current settings. Do you want to continue? [y/N]: ".
*   **AND** I type `N` and press Enter (or just press Enter, accepting the default choice).
*   **THEN** the system should display a message indicating that the operation was cancelled, such as "Initialization cancelled. Your existing .env file has not been changed.".
*   **AND** the command should terminate gracefully.
*   **AND** the content of the `.env` file should remain completely unchanged, still containing `JULES_API_KEY=my_preserved_key`.

**Scenario: UAT-01-005 - System Re-prompts for a Required API Key if User Provides Empty Input**

*   **GIVEN** I am running the `init` command in a clean environment.
*   **AND** I have all the necessary prerequisites installed.
*   **WHEN** the system prompts me for the `JULES_API_KEY`.
*   **AND** I accidentally press the Enter key without typing a value.
*   **THEN** the system should not proceed to the next prompt.
*   **AND** it should instead display an informative error message on the next line, such as "This value is required. Please provide your JULES_API_KEY: ".
*   **AND** the system should then wait for my input for the `JULES_API_KEY` again.
*   **AND** I then enter a valid value, `a_valid_key`.
*   **THEN** the system should accept the value and proceed to the next prompt for the `E2B_API_KEY`.
*   **AND** the final generated `.env` file must contain the line `JULES_API_KEY=a_valid_key`.
