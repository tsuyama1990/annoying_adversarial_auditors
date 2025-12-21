# AC-CDD Internal Development Flow

This document explains the internal architecture, logic, and resources used by the AC-CDD agent system.
It is designed to provide complete transparency into "who is doing what" during the development lifecycle.

## 🏗 System Architecture

AC-CDD utilizes a **Hybrid Agent System** orchestrated by **LangGraph**. It combines the autonomous capabilities of Google's Jules API with the precision editing and auditing power of the `aider` CLI.

### Role & Tool Mapping

| Role | Tool / API | Model Configuration | Responsibility |
|---|---|---|---|
| **Architect** | **Google Jules API** | Standard Jules Model | Analyzes requirements (`ALL_SPEC.md`), designs architecture, and generates `SPEC.md` and `UAT.md`. Operates in a text-only mode (no file execution). |
| **Coder (Initial)** | **Google Jules API** | Standard Jules Model | Performs the **Initial Implementation** (Iteration 0). Has access to file system and terminal tools to scaffold the project from scratch. |
| **Coder (Fixer)** | **aider (CLI)** | `SMART_MODEL` (e.g., Claude 3.5 Sonnet) | Handles **Refinement & Repair** (Iteration > 0). Uses `aider`'s superior code editing capabilities to apply fixes based on audit feedback. |
| **Auditor** | **aider (CLI)** | `FAST_MODEL` (e.g., Gemini 2.0 Flash) | Strictly reviews code in **Read-Only** mode. Leverages `aider`'s Repository Map to understand context and detect issues across the codebase. |

## 🔄 Detailed Workflow Logic

The system operates in two main phases: **Architecture** and **Coding**.

### 1. Architect Phase (`gen-cycles`)
*   **Input**: `dev_documents/ALL_SPEC.md` (User Requirements)
*   **Process**:
    1.  **JulesClient** initiates a session with the Architect Persona (`ARCHITECT_INSTRUCTION.md`).
    2.  Jules analyzes requirements and outputs design documents in a strict `FILENAME:` format.
    3.  The client parses these blocks and writes them to disk.
*   **Output**: `SYSTEM_ARCHITECTURE.md`, `CYCLE{xx}/SPEC.md`, `CYCLE{xx}/UAT.md`.

### 2. Coder Phase (`run-cycle --auto`)
This phase uses a **Fixed Iteration Loop** (default: 3 rounds) to force continuous improvement.

```mermaid
graph TD
    Start([Start Cycle]) --> Checkout[Checkout Branch]
    Checkout --> Loop{Iteration Loop}

    Loop -->|Iter = 1| Jules[Jules (Initial Implementation)]
    Loop -->|Iter > 1| AiderFix[Aider (Fixer / Smart Model)]

    Jules --> RunTests[Run Tests]
    AiderFix --> RunTests

    RunTests --> UATEval[UAT Evaluation (Gemini)]
    UATEval --> StrictAudit[Strict Audit (Aider / Fast Model)]

    StrictAudit -->|Feedback| Loop

    Loop -->|Max Iters Reached| Merge[Commit & Merge]
```

#### Step-by-Step Logic
1.  **Iteration 1 (Creation)**:
    *   **Agent**: **Jules**.
    *   **Action**: Reads `SPEC.md` and implements the core logic from scratch.
2.  **Verification**:
    *   **Tests**: `pytest` runs to capture logs.
    *   **UAT**: The `QA Analyst` agent (Internal Gemini) evaluates test logs against `UAT.md`.
3.  **Strict Audit**:
    *   **Agent**: **Aider** (Read-Only).
    *   **Logic**: Reviews the code against `AUDITOR_INSTRUCTION.md`. Even if the code works, it *must* find improvements (optimization, refactoring, robustness).
4.  **Iteration 2+ (Refinement)**:
    *   **Agent**: **Aider** (Fixer).
    *   **Action**: Takes the Audit Feedback and applies precise code edits.
5.  **Completion**:
    *   The loop continues until `MAX_ITERATIONS` (defined in config) is reached.
    *   The final state is committed to the feature branch.

## 🤖 Configuration & Resources

The system's behavior is controlled via environment variables and configuration files.

### Environment Variables (`.env`)

| Variable | Usage | Recommended Value |
|---|---|---|
| `JULES_API_KEY` | Authentication for Google Jules API (Architect/Initial Coder). | `required` |
| `GEMINI_API_KEY` | Primary key for Gemini Models (Auditor/QA). | `required` |
| `ANTHROPIC_API_KEY` | Primary key for Claude Models (Fixer via Aider). | `required` |
| `SMART_MODEL` | Model ID for **Fixer** (Aider). High capability required. | `claude-3-5-sonnet-20241022` |
| `FAST_MODEL` | Model ID for **Auditor** (Aider). Speed & Context required. | `gemini-2.0-flash-exp` |

### Configuration Files

*   **`ac_cdd_config.py`**: Central Python configuration.
    *   `MAX_ITERATIONS`: Controls the number of refinement loops (Default: 3).
    *   `AiderConfig`: Maps `SMART_MODEL`/`FAST_MODEL` to `aider` arguments.
*   **`dev_documents/templates/`**: System Prompts.
    *   `ARCHITECT_INSTRUCTION.md`: Prompts for Jules (Architect).
    *   `CODER_INSTRUCTION.md`: Prompts for Jules (Initial Coder).
    *   `AUDITOR_INSTRUCTION.md`: Prompts for Aider (Auditor). **Must remain Strict.**

## Why this Architecture?

*   **Jules** is excellent at "0 to 1" creation and understanding broad project goals, making it ideal for the Architect and Initial Coder roles.
*   **Aider** is the SOTA (State of the Art) tool for applying diffs and editing existing code, making it superior for the "Fixer" role where precise refactoring is needed.
*   **LangGraph** acts as the supervisor, ensuring the process doesn't stop at the first "pass" but forces the code to undergo rigorous refinement cycles.
