# AI-Native Development Template

## 🚀 Getting Started (First Time Experience)

### 1. Prerequisites
Ensure you have the following tools installed:
- `uv` (Python Package Manager)
- `jules` & `gemini` (Google AI CLI Tools)

Run the doctor command to verify your environment:
```bash
uv run manage.py doctor
```

### 2\. Ad-hoc Workflow (Quick Fixes)

Use these commands for quick iterations outside of a formal cycle.

**Auto-Fix (Test Driven Repair):**
Runs tests and automatically assigns Jules to fix failures.

```bash
uv run manage.py fix
```

**Strict Audit (Code Review):**
Uses Gemini to strictly review your `git diff` and assigns Jules to implement fixes.

```bash
uv run manage.py audit
```

### 3\. Cycle-Based Workflow (Contract-Driven)

For formal feature development.

```bash
# Start a new development cycle
uv run manage.py new-cycle "user-auth-feature"

# Run the implementation loop (Contract -> Test -> Code)
uv run manage.py start-cycle "user-auth-feature"
```
