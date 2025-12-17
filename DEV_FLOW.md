# Development Flow (AC-CDD)

## Graph Architecture

The core orchestration is handled by `LangGraph`.

```mermaid
stateDiagram-v2
    [*] --> CheckArchitecture
    CheckArchitecture --> Structurer: No SYSTEM_ARCHITECTURE
    CheckArchitecture --> Planner: SYSTEM_ARCHITECTURE Exists
    Structurer --> Planner: Generates SYSTEM_ARCHITECTURE
    Planner --> SpecWriter: Reads SYSTEM_ARCHITECTURE -> Generates Cycle Plan
    SpecWriter --> Coder: Schema & Property Tests Ready

    state ImplementationLoop {
        Coder --> Tester: Code Implemented
        Tester --> Auditor: Tests Passed
        Tester --> Coder: Tests Failed (Fix)
        Auditor --> UAT: Strict Audit Passed
        Auditor --> Coder: Audit Failed (Fix)
    }

    UAT --> Coder: UAT Failed (Fix)
    UAT --> [*]: UAT Passed (Cycle Complete)
```

## Data Flow

1. **CycleState**: Passed between nodes, containing `cycle_id`, `plan`, `audit_result`, `sandbox_id`.
2. **Sandbox**:
   - `SandboxRunner` syncs `src/` and `tests/` to E2B.
   - Executes `pytest`, `ruff`, `mypy`.
   - Returns logs/exit codes to Graph.
3. **Local FS**:
   - Agents read/write source files locally.
   - "Source of Truth" is always local Git repo.

## Agents

- **Structurer**: System Architect (Gemini 2.5 Pro)
- **Planner**: Architect (Gemini 2.5 Pro)
- **Coder**: Senior Engineer (Gemini 2.5 Pro)
- **QA Analyst**: Test Engineer (Gemini 2.5 Flash)
- **Auditor**: Security Specialist (Gemini 2.5 Pro)
