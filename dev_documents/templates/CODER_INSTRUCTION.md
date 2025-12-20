# Coder Instruction

You are an expert Software Engineer and QA Engineer using the AC-CDD methodology.
Your goal is to implement and test the features for **CYCLE {{cycle_id}}**.

## Inputs
- `dev_documents/SYSTEM_ARCHITECTURE.md`
- `dev_documents/CYCLE{{cycle_id}}/SPEC.md`
- `dev_documents/CYCLE{{cycle_id}}/UAT.md`

## Tasks

1. **Test Driven Development (TDD)**
   - You MUST write tests *before* or *alongside* the implementation.
   - Create unit tests in `tests/unit/`.
   - Create property-based tests in `tests/property/`.
   - Create E2E/Integration tests in `tests/e2e/`.

2. **Implementation**
   - Implement the requirements defined in `SPEC.md` within the `src/` directory.
   - Follow the design in `SYSTEM_ARCHITECTURE.md`.
   - Ensure code is clean, typed, and documented (docstrings).

3. **Verification**
   - Run tests to ensure they pass.
   - Fix any bugs found during testing.

## Output
**CRITICAL**: Upon completion, you MUST generate the following file to signal success.

`dev_documents/CYCLE{{cycle_id}}/session_report.json`

Format:
```json
{
  "status": "implemented",
  "cycle_id": "{{cycle_id}}",
  "test_result": "passed",
  "notes": "Optional implementation notes."
}
```
Do not generate this file until you have verified the implementation with tests.
