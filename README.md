# Autonomous Development Environment (AC-CDD)

An AI-native development environment implementing **Cycle-based Contract-Driven Development**.
Powered by **LangGraph** and **E2B Code Interpreter**.

## Architecture

This project uses a State Graph to orchestrate AI agents for planning, coding, testing, and auditing.

```mermaid
graph TD
    Planner --> SpecWriter
    SpecWriter --> Coder
    Coder --> Tester
    Tester -- Fail --> Coder
    Tester -- Pass --> Auditor
    Auditor -- Fail --> Coder
    Auditor -- Pass --> UAT
    UAT -- Fail --> Coder
    UAT -- Pass --> End
```

### Components

- **LangGraph**: Manages state and flow control (`src/ac_cdd/graph.py`, `src/ac_cdd/state.py`).
- **E2B Code Interpreter**: Safely executes tests and audits in a cloud sandbox (`src/ac_cdd/sandbox.py`).
- **Pydantic AI**: Provides structured agent outputs (`src/ac_cdd/agents.py`).

## Setup

1. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure Environment**:
   Copy `.env.example` to `.env` and set your API keys.
   ```bash
   cp dev_documents/templates/.env.example .env
   ```

   **Required Keys:**
   - `GEMINI_API_KEY`: For AI Agents.
   - `E2B_API_KEY`: For Sandbox execution (Get one at [e2b.dev](https://e2b.dev)).
   - `LOGFIRE_TOKEN`: (Optional) For observability.

## Usage

### Start a Development Cycle
```bash
uv run manage.py start-cycle 01
```
This will:
1. Plan features (SPEC/Schema/UAT).
2. Generate property tests.
3. Implement code.
4. Run tests in E2B Sandbox.
5. Audit code (Static Analysis + LLM).
6. Run UAT in E2B Sandbox.

### Create a New Cycle
```bash
uv run manage.py new-cycle 02
```

### Ad-hoc Commands
- **Audit**: `uv run manage.py audit` (Review git diffs)
- **Fix**: `uv run manage.py fix` (Fix failed tests)
- **Check Env**: `uv run manage.py doctor`

## Development Flow

See [DEV_FLOW.md](./DEV_FLOW.md) for detailed architecture diagrams.
