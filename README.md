# Autonomous Development Environment (AC-CDD)

An AI-Native Cycle-Based Contract-Driven Development Environment.

## Key Features

*   **🚀 Automated Rapid Application Design (Auto-RAD)**
    *   Just define your raw requirements in `ALL_SPEC.md`.
    *   The `gen-cycles` command automatically acts as an **Architect**, generating `SYSTEM_ARCHITECTURE.md`, detailed `SPEC.md`, and `UAT.md` (User Acceptance Tests) for every development cycle.

*   **🛡️ Committee of Code Auditors**
    *   No more "LGTM" based on loose checks.
    *   An automated **Committee of Auditors** (3 independent audit passes) performs strict, multi-pass code reviews.
    *   The system iteratively fixes issues until the code passes ALL auditors' quality gates.
    *   **Total: Up to 6 audit-fix cycles** (3 auditors × 2 reviews each) per development cycle for maximum code quality.

*   **🔒 Secure Sandboxed Execution**
    *   **Fully Remote Architecture**: All code execution, testing, and AI-based fixing happens inside a secure, ephemeral **E2B Sandbox**.
    *   Your local environment stays clean. No need to install complex dependencies locally.
    *   The system automatically syncs changes back to your local machine.

*   **✅ Integrated Behavior-Driven UAT**
    *   Quality is not just about code style; it's about meeting requirements.
    *   The system automatically executes tests and verifies them against the behavior definitions in `UAT.md` before any merge.

*   **🤖 Hybrid Agent Orchestration**
    *   Combines the best of breed:
        *   **Google Jules**: For long-context architectural planning, initial implementation, and iterative refinement (fixing).
        *   **LLMReviewer**: For fast, direct API-based code auditing using various LLM providers.
        *   **LangGraph**: For robust state management and supervisor loops.

## Deployment Architecture

AC-CDD is designed as a **containerized CLI tool**. You do not clone the tool's source code into your project. Instead, you run the AC-CDD Docker container, which mounts your project directory.

**Directory Structure on User's Host:**

```
📂 my-awesome-app/ (Your Repository)
 ├── 📂 src/              <- Your source code
 ├── 📂 dev_documents/    <- Specifications (ALL_SPEC.md, etc.)
 ├── .env                 <- API Keys
 └── docker-compose.yml   <- Runner configuration
```

**Inside the Docker Container:**

```
[🐳 ac-cdd-core]
 ├── /app (WORKDIR)       <- Your project is mounted here
 ├── /opt/ac-cdd/templates <- Internal system prompts & resources
 └── Python Environment   <- uv, LangGraph, Agents pre-installed
```

## Getting Started

### Prerequisites

*   Docker Desktop or Docker Engine
*   `git`
*   `gh` (GitHub CLI) - Required for authentication with GitHub

### Installation

1.  **Setup `docker-compose.yml`:**
    Download the distribution `docker-compose.yml` to your project root, or create one:

    ```yaml
    version: '3.8'
    services:
      ac-cdd:
        image: tsuyama1990/ac-cdd-agent:latest
        container_name: ac-cdd-agent
        volumes:
          - .:/app
          - ${HOME}/.ac_cdd/.env:/root/.ac_cdd/.env
        env_file:
          - .env
        environment:
          - HOST_UID=${UID:-1000}
          - HOST_GID=${GID:-1000}
        command: ["ac-cdd"]
        stdin_open: true
        tty: true
    ```

2.  **Create an Alias (Recommended):**
    Add this to your shell profile (`.zshrc` or `.bashrc`) for easy access:
    ```bash
    alias ac-cdd='docker-compose run --rm ac-cdd'
    ```

### Configuration

The system is configured via environment variables. Run `ac-cdd init` to generate a `.env.example` file in the `.ac_cdd/` directory with all necessary configuration options.

#### Quick Setup

1. **Initialize your project:**
   ```bash
   ac-cdd init
   ```

2. **Copy the example configuration:**
   ```bash
   cp .ac_cdd/.env.example .env
   ```

3. **Fill in your API keys in `.env`**

#### API Keys

The `.env` file should contain:

```env
# Required API Keys
JULES_API_KEY=your-jules-api-key-here
E2B_API_KEY=your-e2b-api-key-here
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Simplified Model Configuration
# These two settings control ALL agents (Auditor, QA Analyst, Reviewer, etc.)
SMART_MODEL=openrouter/meta-llama/llama-3.3-70b-instruct:free
FAST_MODEL=openrouter/nousresearch/hermes-3-llama-3.1-405b:free
```

#### Model Configuration (Simplified)

You only need to set **two environment variables** for model configuration:

- **`SMART_MODEL`**: Used for complex tasks (code editing, architecture, auditing)
- **`FAST_MODEL`**: Used for reading and analysis tasks

**Supported Model Formats:**
- OpenRouter: `openrouter/provider/model-name`
- Anthropic: `claude-3-5-sonnet`
- Gemini: `gemini-2.0-flash-exp`

**Advanced Configuration (Optional):**

If you need fine-grained control over specific agents, you can override individual models:

```env
# Override specific agent models (optional)
AC_CDD_AGENTS__AUDITOR_MODEL=openrouter/meta-llama/llama-3.3-70b-instruct:free
AC_CDD_AGENTS__QA_ANALYST_MODEL=openrouter/meta-llama/llama-3.3-70b-instruct:free

# Override reviewer models (optional)
AC_CDD_REVIEWER__SMART_MODEL=claude-3-5-sonnet
AC_CDD_REVIEWER__FAST_MODEL=gemini-2.0-flash-exp
```

## 🚀 Usage

### 1. Initialize Project

Navigate to your empty project folder and run:

```bash
ac-cdd init
```

This creates the `dev_documents/` structure and `pyproject.toml` (if missing) in your current directory.

**Next Step:** Edit `dev_documents/ALL_SPEC.md` with your raw project requirements.

### 2. Generate Architecture & Start Session

```bash
ac-cdd gen-cycles
```

This acts as the **Architect**:
- Reads `ALL_SPEC.md`
- Generates `SYSTEM_ARCHITECTURE.md`, `SPEC.md`, and `UAT.md`
- Creates a **development session** and branches (e.g., `dev/session-{timestamp}`)

**Session is saved** to `.ac_cdd_session.json` for automatic resumption.

### 3. Run Development Cycles

```bash
# Run individual cycles (automated auditing enabled by default)
ac-cdd run-cycle --id 01
ac-cdd run-cycle --id 02

# Or run all cycles sequentially
ac-cdd run-cycle --id all

# Disable automated auditing (not recommended)
ac-cdd run-cycle --id 01 --no-auto
```

Each cycle:
- Creates branch: `dev/session-{timestamp}/cycle{id}`
- Implements features via Jules
- Runs **Committee of Auditors** automatically (3 auditors × 2 reviews each)
- Auto-merges to **integration branch** (not main)

### 4. Finalize Session

```bash
ac-cdd finalize-session
```

Creates a **final Pull Request** from integration branch to `main`.

## Contributing

If you want to modify the AC-CDD framework itself:

1.  Clone this repository.
2.  Modify code in `dev_src/ac_cdd_core`.
3.  Rebuild the Docker image: `docker build -t ac-cdd .`
4.  Test your changes using the alias.

## License

[License Name]
