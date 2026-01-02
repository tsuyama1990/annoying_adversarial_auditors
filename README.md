# Autonomous Development Environment (AC-CDD)

An AI-Native Cycle-Based Contract-Driven Development Environment.

## Key Features

*   **🚀 Automated Rapid Application Design (Auto-RAD)**
    *   Just define your raw requirements in `ALL_SPEC.md`.
    *   The `gen-cycles` command automatically acts as an **Architect**, generating `SYSTEM_ARCHITECTURE.md`, detailed `SPEC.md`, and `UAT.md` (User Acceptance Tests) for every development cycle.

*   **🛡️ Committee of Code Auditors**
    *   No more "LGTM" based on loose checks.
    *   An automated **Committee of Auditors** (3 independent auditors, each reviewing 2 times) performs strict, multi-pass code reviews.
    *   The system iteratively fixes issues (using Jules via session resumption) until the code passes all auditors' quality gates.
    *   **Total: 6 audit-fix cycles** per development cycle for maximum code quality.

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
 ├── ac_cdd_config.py     <- Project Configuration
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

1.  **Pull the Docker Image (or build it):**
    ```bash
    docker build -t ac-cdd .
    ```
    *(Assuming you have the Dockerfile locally, or pull from a registry if published)*

2.  **Create an Alias (Recommended):**
    Add this to your shell profile (`.zshrc` or `.bashrc`) for easy access:
    ```bash
    alias ac-cdd='docker run -it --rm -v $(pwd):/app -v $HOME/.config/gh:/root/.config/gh --env-file .env ac-cdd'
    ```
    *Note: We mount `~/.config/gh` to share GitHub credentials.*

### Configuration

The system is configured via `.env` and `ac_cdd_config.py`.

#### API Keys

Create a `.env` file in your project root:

```env
# Jules API (Architect/Coder)
JULES_API_KEY=your_jules_key

# Sandbox (Execution)
E2B_API_KEY=e2b_...

# Models (Auditor/QA)
OPENROUTER_API_KEY=sk-or-...
# Or specific keys: GEMINI_API_KEY, ANTHROPIC_API_KEY
```

#### Multi-Model Configuration

You can configure different models for different agents to optimize for cost and intelligence.

**Example `.env` configuration (Hybrid):**

```env
# Smart model for Jules (fixing/refinement) - High capability required
SMART_MODEL=claude-3-5-sonnet-20241022

# Fast model for LLMReviewer (auditing) & QA Analyst - Speed & context required
FAST_MODEL=gemini-2.0-flash-exp
```

## 🚀 Usage

### 1. Initialize Project

Navigate to your empty project folder and run:

```bash
ac-cdd init
```

This creates the `dev_documents/` structure and a default `ac_cdd_config.py` in your current directory.

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
# Run individual cycles (session auto-loaded)
ac-cdd run-cycle --id 01
ac-cdd run-cycle --id 02

# Or run all cycles sequentially
ac-cdd run-cycle --id all --auto
```

Each cycle:
- Creates branch: `dev/session-{timestamp}/cycle{id}`
- Implements features via Jules
- Runs **6 audit-fix cycles** (3 auditors × 2 reviews each)
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
