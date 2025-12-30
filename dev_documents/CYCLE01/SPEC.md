# SPEC.md - Cycle 01: Core CLI, Initialization, and Configuration

## 1. Summary

This specification provides a detailed blueprint for the foundational first cycle of the Autonomous Development Environment (AC-CDD) project. The singular focus of Cycle 01 is to construct the essential scaffolding upon which all future, more complex functionality will be built. This entails the creation of a robust, user-friendly command-line interface (CLI) and a comprehensive configuration management system. The primary deliverable for this cycle is a fully functional `init` command. This command will serve as the user's first point of contact with the system, and as such, the experience must be seamless, intuitive, and foolproof. Its responsibilities go beyond merely creating a configuration file; it must act as a guardian of the user's environment, performing critical prerequisite checks to verify that all necessary external tools are installed and accessible. This proactive validation is crucial for preventing difficult-to-diagnose errors in later stages of the workflow. The work in this cycle is paramount, as it establishes the core architectural patterns for the entire application, including the command structure, the separation of concerns between the CLI and backend services, the conventions for user-facing communication, and the secure handling of sensitive data like API keys. By the conclusion of this cycle, a new user will have a clear and simple path to readiness: they will be able to clone the repository, install dependencies with a single command, and then execute the `init` command to fully prepare their local environment for the advanced AI-driven development tasks that will be introduced in subsequent cycles. This cycle does not involve any AI agents or remote execution; its success is measured by the creation of a stable, reliable, and well-designed local foundation.

## 2. System Architecture

The architecture for Cycle 01 is intentionally constrained to the user's local machine, focusing on establishing a clean and maintainable structure for the CLI application itself. There are no external dependencies beyond the user's shell environment. The system comprises three principal components: the Command-Line Interface (CLI) layer, the Configuration Management service, and the Project Initialization service.

**1. Command-Line Interface (CLI) Layer:**
This is the outermost layer of the system and the sole point of interaction for the user in this cycle. It will be implemented using the `Typer` library, chosen for its modern features, automatic help generation, and robust type-hinting-based validation. The initial implementation will establish the main application object and define the `init` command. The responsibilities of this layer are to:
- Parse and interpret the commands and arguments provided by the user.
- Invoke the appropriate backend services to execute the requested business logic.
- Serve as the primary channel for all user-facing communication. To this end, it will be tightly integrated with a presentation service (using the `rich` library) to ensure that all output—whether it's a success message, a user prompt, a warning, or a critical error—is clear, consistently formatted, and easy for the user to understand. This layer will also be responsible for implementing a global exception handler, ensuring that any unexpected errors in the backend services are caught gracefully and presented to the user without overwhelming them with a raw stack trace.

**2. Configuration Management Service:**
This component is the central authority for all application settings. Its core responsibility is to provide a unified, validated, and easily accessible source of configuration data. It will be designed to read from two distinct sources, separating secrets from general settings:
- **`.env` file:** This file, located at the project root, will be the sole repository for sensitive information, primarily the various API keys (`JULES_API_KEY`, `E2B_API_KEY`, etc.). This file is intended to be managed by the user and should be included in `.gitignore` by default.
- **`ac_cdd_config.py`:** A Python file for non-sensitive, user-configurable parameters, such as model names, temperature settings, or timeouts.
To ensure robustness, the service will be built using the `pydantic-settings` library. This allows us to define all configuration variables in a single, strongly-typed `Settings` class. At application startup, Pydantic will automatically read from the specified sources, parse the values, and validate them against the defined types. This proactive validation is a critical design choice, as it prevents a large class of runtime errors caused by missing or malformed configuration, providing a "fail-fast" mechanism that improves the system's overall reliability. The loaded and validated settings will be exposed to the rest of the application via a single, importable `settings` object.

**3. Project Initialization Service:**
This service encapsulates the core business logic of the `init` command. Its responsibilities are divided into two main areas:
- **Prerequisite Validation:** Before taking any action, this service will perform a thorough scan of the user's environment to ensure it meets the system's requirements. It will systematically check for the presence and executability of all required command-line tools, specifically `git`, `gh` (the GitHub CLI), and `uv`. If any of these dependencies are not found in the system's `PATH`, the service will immediately halt the process and raise a specific, informative exception, which the CLI layer will then present to the user.
- **`.env` File Generation:** This is the primary action of the `init` command. The service will use a template file (`.env.example`) as the canonical source of required keys. It will read this template and then guide the user through an interactive session in the terminal, prompting them for the value of each key one by one. This interactive approach is a deliberate design choice to enhance security, as it prevents sensitive keys from being saved in the user's shell history. The service will also handle the case where a `.env` file already exists, prompting the user for confirmation before overwriting it to prevent accidental data loss.

The data flow for this cycle is straightforward and linear: The user executes the `init` command. The CLI layer receives the command and calls the Project Initialization Service. This service first performs the prerequisite checks. If successful, it proceeds to the interactive `.env` file generation process, and upon completion, the system is fully configured.

## 3. Design Architecture

The internal design for Cycle 01 emphasizes a clean, service-oriented architecture that promotes testability and separation of concerns.

**1. File and Directory Structure:**
The project's core logic will be organized within the `dev_src/ac_cdd_core/` package to keep it separate from the user's own project code (`src/`).
- `manage.py`: This file at the project root will be the main entry point. It will be kept minimal, responsible only for creating the main `Typer` application instance and registering the command modules.
- `dev_src/ac_cdd_core/`:
  - `cli.py`: This module will house the implementation of the `Typer` commands. For this cycle, it will contain the `init()` function, which orchestrates the calls to the necessary backend services.
  - `config.py`: This module will define the `Settings` class using `pydantic-settings`. It will declare all the required environment variables with their types (e.g., `JULES_API_KEY: str`). It will also instantiate and export the singleton `settings` object that the rest of the application will import to access configuration values.
  - `services/`: This new directory will contain the modules for the backend business logic, ensuring it is decoupled from the CLI presentation layer.
    - `project.py`: This module will contain the `ProjectManager` class. This class will encapsulate all the logic related to the project's setup and initialization, including the methods for checking prerequisites and generating the `.env` file.
  - `presentation.py`: This module will define the `ConsolePresenter` class. It will be a wrapper around the `rich.console.Console` object, providing a standardized set of methods (`show_message`, `show_error`, `prompt_user`) for all console I/O. This ensures a consistent and high-quality user experience and decouples the core logic from the specifics of how information is displayed.
- `dev_documents/templates/`: This directory will hold any template files used by the system.
  - `.env.example`: This file will serve as the template for the `.env` file generation. It will list all the required keys, possibly with comments explaining their purpose.

**2. Key Classes and Functions:**
- **`manage.py`:**
  - `app = typer.Typer()`: The main application instance.
  - `app.add_typer(cli.app, name="manage")`: Registers the command group from the `cli` module.
- **`ac_cdd_core.cli.py`:**
  - `@app.command()` `def init():`: The function that implements the `init` command. It will be the orchestrator for this workflow. Its role is to instantiate the `ProjectManager` and `ConsolePresenter`, and then invoke the manager's methods within a `try...except` block. This block will catch any specific exceptions thrown by the service (e.g., `PrerequisiteNotFoundException`) and use the presenter to display a user-friendly error message before exiting the application with a non-zero status code.
- **`ac_cdd_core.config.py`:**
  - `class Settings(BaseSettings):`: The Pydantic model for settings. It will include fields like `JULES_API_KEY: SecretStr` to ensure secrets are handled securely and not accidentally leaked in logs.
  - `settings = Settings()`: The globally accessible, validated settings instance.
- **`ac_cdd_core.services.project.py`:**
  - `class ProjectManager:`:
    - `check_prerequisites(self) -> None`: This method will iterate through a list of required command names (e.g., `['git', 'gh', 'uv']`). For each, it will use `shutil.which()` to determine if the command exists in the user's `PATH`. If `shutil.which()` returns `None` for any command, it will raise a custom `PrerequisiteNotFoundException` containing the name of the missing command.
    - `create_env_file(self) -> None`: This method will first check if a `.env` file already exists. If it does, it will use the `ConsolePresenter` to ask the user for overwrite confirmation. If confirmed, or if no file exists, it will read the `.env.example` template, parse out the key names, and then loop through them, using the `ConsolePresenter`'s prompt method to securely ask the user for each value. The collected key-value pairs will then be written to the `.env` file.
- **`ac_cdd_core.presentation.py`:**
  - `class ConsolePresenter:`:
    - `show_message(self, message: str, style: str = "info")`: A method for printing styled text.
    - `show_error(self, message: str)`: A method for printing errors in a standardized, high-visibility style.
    - `confirm(self, prompt: str) -> bool`: A wrapper for `typer.confirm`.
    - `prompt_for_value(self, prompt: str, is_secret: bool = False) -> str`: A wrapper for `typer.prompt` that handles secret inputs.

## 4. Implementation Approach

The implementation will be methodical, building the system from the inside out—from configuration and services to the final CLI integration.

**Step 1: Establish Project Structure and Configuration**
- Create the file and directory structure as laid out in the design section.
- Implement the `Settings` class in `ac_cdd_core/config.py`, defining all the required environment variables.
- Create the `.env.example` template file in `dev_documents/templates/`.

**Step 2: Develop the Presentation Layer**
- Implement the `ConsolePresenter` class in `ac_cdd_core/presentation.py`. This class will abstract the `rich` and `typer` I/O functions to provide a consistent interface for the rest of the application.

**Step 3: Implement the `ProjectManager` Service**
- Implement the `ProjectManager` class in `ac_cdd_core/services/project.py`.
- First, implement the `check_prerequisites` method. Define a custom exception, `PrerequisiteNotFoundException`, that it can raise.
- Second, implement the `create_env_file` method. This method will be carefully designed to be robust, handling file existence checks and using the `ConsolePresenter` for all user interactions.

**Step 4: Implement the CLI Command**
- Implement the `init` command function in `ac_cdd_core/cli.py`. This function will tie all the other components together.
- It will instantiate the `ConsolePresenter` and `ProjectManager`.
- It will call the manager's methods in the correct order: first `check_prerequisites`, then `create_env_file`.
- A comprehensive `try...except` block will be used to catch errors from the service layer and present them cleanly to the user.

**Step 5: Write Unit Tests**
- In parallel with the implementation, unit tests will be written in the `tests/unit/` directory.
- Tests for `ProjectManager` will use mocking extensively. `shutil.which` will be mocked to simulate both the presence and absence of prerequisites. The `ConsolePresenter` dependency and file system operations (`open`, `write`) will also be mocked to test the `create_env_file` logic without actual I/O.
- Tests for the `cli.py` `init` command will use the `CliRunner` from `Typer`. The `ProjectManager` will be mocked to test the command's orchestration logic. For example, a test will simulate the manager raising a `PrerequisiteNotFoundException` and assert that the `CliRunner`'s output contains the expected user-friendly error message.

**Step 6: Manual Integration Testing**
- After the unit tests are passing, a final manual test will be performed by running `uv run manage.py init` in a clean checkout of the repository to verify the end-to-end user experience.

## 5. Test Strategy

The test strategy for Cycle 01 is focused on ensuring the reliability and robustness of the CLI and its foundational services through a combination of unit and integration testing.

**Unit Testing Approach:**
The primary goal of the unit tests is to validate the logic of each component in complete isolation.
- **`ProjectManager`:** This class will be the most heavily unit-tested component.
  - For `check_prerequisites`, we will mock `shutil.which`. One test will have the mock return a valid path for all checked commands, and we'll assert that the method completes without raising an exception. A separate test for each prerequisite will have the mock return `None`, and we will assert that the specific `PrerequisiteNotFoundException` is raised with the correct error message.
  - For `create_env_file`, we will mock the file system (using `pyfakefs` or by mocking `pathlib.Path` methods) and the `ConsolePresenter`. We will test the "happy path" where no `.env` file exists, asserting that the template is read, the user is prompted for each key, and the final file is written with the correct content. We will also test the overwrite logic by simulating a pre-existing file and mocking the user's confirmation (`True` and `False`) and asserting the correct behavior in each case.
- **`config.py`:** Tests for the `Settings` object will involve setting environment variables within the test process itself and then importing and inspecting the `settings` object to assert that the variables were loaded and cast to the correct types.
- **`cli.py`:** The `init` command will be tested using `typer.testing.CliRunner`. We will mock the entire `ProjectManager` class. In one test, we will simulate a successful run and assert that the manager's `check_prerequisites` and `create_env_file` methods were called in the correct sequence. In another test, we will configure the mocked `check_prerequisites` method to raise a `PrerequisiteNotFoundException` and assert that the CLI output captured by the `CliRunner` contains the expected error message and that the `create_env_file` method was not called.

**Integration Testing Approach:**
Integration tests will verify that the layers of the application work together correctly.
- **CLI and Service Integration:** An integration test will be created for the `init` command that mocks the lower-level system dependencies instead of the `ProjectManager` itself. Specifically, we will mock `shutil.which` and the `ConsolePresenter`'s prompt methods. When we invoke the `init` command via `CliRunner`, this test will verify that the call flows correctly from the `cli.py` module down into the `ProjectManager` service and that the service's logic correctly invokes the mocked system functions.
- **File System Integration:** A key integration test will use a temporary directory. It will create a dummy `.env.example` file within it. It will then run the `init` command (with user input mocked) and allow the `ProjectManager` to perform real file I/O within this temporary directory. After the command completes, the test will read the generated `.env` file from the temporary directory and assert that its contents are exactly as expected. This provides high confidence that the file generation process is working correctly end-to-end.
