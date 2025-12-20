# Developer Flow & Architecture

This document describes the architectural flow and developer experience for the AC-CDD system.

## Core Philosophy

**AC-CDD (Cycle-Based Contract-Driven Development)** is a methodology that uses AI agents to strictly enforce quality gates during rapid iteration.

1.  **Contract-First**: Everything starts with a specification (Contract).
2.  **Cycle-Based**: Development happens in discrete, manageable cycles.
3.  **Strict Auditing**: No code is merged without passing a strict, multi-pass AI audit.

## Architecture

The system is built on **LangGraph** and orchestrates two main workflows:

### 1. Architect Workflow (`gen-cycles`)

*   **Goal**: Define the system and break it down into implementation cycles.
*   **Agent**: Jules (Architect Persona).
*   **Inputs**: `dev_documents/templates/ARCHITECT_INSTRUCTION.md`.
*   **Outputs**:
    *   `SYSTEM_ARCHITECTURE.md`: High-level design.
    *   `ALL_SPEC.md`: Detailed specifications for all cycles.
    *   `UAT.md`: User Acceptance Testing criteria.

### 2. Coder Workflow (`run-cycle`)

*   **Goal**: Implement a specific cycle (e.g., Cycle 01).
*   **Agents**:
    *   **Coder** (Jules): Writes code and tests in `src/`.
    *   **QA Analyst** (Gemini Flash): Analyzes test logs against `UAT.md`.
    *   **Auditor** (Gemini Pro): Strictly reviews code changes against best practices and security rules.
*   **Process**:
    1.  **Checkout**: Creates `feat/cycle{id}`.
    2.  **Coder Session**: Generates code based on `SPEC.md` and `ARCHITECT_INSTRUCTION.md`.
    3.  **Test**: Runs `pytest` in a sandbox or local environment.
    4.  **UAT**: QA Analyst evaluates pass/fail.
    5.  **Audit**: Auditor reviews code. Must pass 3 consecutive checks (Triple Check) or satisfies the "Strict" criteria.
    6.  **Commit**: Code is committed only if all gates pass.

## Directory Structure

To separate the tooling from the product being built, we use the following structure:

*   **`dev_src/`**: Contains the AC-CDD core application code (the agents, CLI, graph logic).
*   **`src/`**: Reserved for **User Product Code**. The agents will create files here.
*   **`dev_documents/`**: Stores project documentation, cycle artifacts, and templates.
    *   `templates/`: Instructions for agents (`ARCHITECT_INSTRUCTION.md`, `CODER_INSTRUCTION.md`).
    *   `CYCLE{xx}/`: Artifacts specific to a cycle.
*   **`tests/`**: Tests for the AC-CDD core. User tests should generally be generated within `src/tests` or alongside code, depending on configuration.

## Configuration & Models

The system is designed to be multi-model capable.

### Environment Variables (`.env`)

*   `JULES_API_KEY`: Mandatory. Authenticates with the Jules backend.
*   `GEMINI_API_KEY`: Default for Auditor/QA.
*   `OPENROUTER_API_KEY`: Optional. Use for accessing other models (Claude, GPT-4) via OpenRouter.

### Model Selection

In `ac_cdd_config.py` (or via `.env` aliases), you can assign specific models to agents:

*   **Auditor**: Needs high reasoning capability. Default: `gemini-2.5-pro` (`SMART_MODEL`).
*   **QA Analyst**: Needs speed and context window. Default: `gemini-2.5-flash` (`FAST_MODEL`).

To use OpenRouter, set the model name with the prefix (e.g., `openrouter/anthropic/claude-3-opus`) and ensure `OPENROUTER_API_KEY` is set.

## Development Workflow for Users

1.  **Initialize**: `uv run manage.py init`
2.  **Design**: Edit `dev_documents/templates/ARCHITECT_INSTRUCTION.md` to describe your app.
3.  **Generate Plan**: `uv run manage.py gen-cycles`
4.  **Review**: Check `ALL_SPEC.md` and `SYSTEM_ARCHITECTURE.md`.
5.  **Implement**: `uv run manage.py run-cycle --id 01`
    *   If Audit fails, the agent will automatically retry with feedback.
    *   If UAT fails, the cycle stops for manual intervention or retry.

## Troubleshooting

*   **Infinite Audit Loops**: If the Auditor keeps rejecting code, check the `audit_feedback` in the logs. You may need to manually intervene or adjust the `AUDITOR_INSTRUCTION.md` template.
*   **Jules Connection**: Ensure `JulesClient` is properly configured and `JULES_API_KEY` is valid.
