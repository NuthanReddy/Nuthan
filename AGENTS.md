# AGENTS.md

## What this repo is
- `Nuthan` is a **practice monorepo**: mostly standalone Python scripts for DS/algorithms + a few mini-systems (`SystemDesign/`, `LLD/`).
- There is no single app entrypoint; changes are usually scoped to one folder/problem.

## Architecture and boundaries (important)
- `DataStructures/` and `Problems/` are the core learning areas; files are generally self-contained and often executable directly (many `if __name__ == "__main__"` blocks).
- `SystemDesign/` contains simulations/prototypes with runtime side effects at module import/execution time (example: `SystemDesign/RateLimiter.py` — now `SystemDesign/Utils/RateLimiter.py` — historically ran a packet loop immediately; it is now guarded by `if __name__ == "__main__"`).
- `SystemDesign/` also includes documentation-first domain folders with large design READMEs (example: `SystemDesign/DistributedCache/README.md`); avoid broad edits there unless requested.
- Logging system appears in two places:
  - package-style implementation: `LLD/LoggerModule/logger/` (`logger.py`, `sinks.py`, `config_reader.py`)
  - script-style split modules: `Utils/` (`LoggerFactory.py`, `PriorityBuffer.py`, etc.)
  Keep edits within one variant unless explicitly unifying both.
- Data/compute experiments are isolated:
  - `PySpark/` builds local Spark sessions (`PySpark/SparkUtils.py`)
  - `Pandas/` holds notebook-like scripts
  - `AI/` mixes Google GenAI (`AI/GoogleAI.py`) and Azure AI Agents SDK experiments (`AI/Agent.py`)

## Developer workflow (repo-specific)
- Python/tooling constraints are defined in `pyproject.toml`: `requires-python = ">=3.10,<3.12"` (despite broader guidance in docs).
- Install deps with `uv`; current canonical setup in `README.md` is `uv sync` (dependencies are currently in main `[project.dependencies]`).
- Run tests with `uv run pytest`.
- Dependency caveat from `README.md`/`pyproject.toml`: `spleeter` constrains pandas compatibility; if you need newer `pandas`, remove or adjust `spleeter` first.

## Conventions you should follow here
- Keep solutions simple/readable; prefer explicit logic over compact tricks (matches `.github/copilot-instructions.md`).
- Use `test_*.py` naming and pytest style (`tests/test_fixtures_scope.py`, `tests/test_sample.py`).
- In `Problems/`, include problem context at file top and handle edge cases (see `Problems/Combinations/MaxPalindromes.py`).
- Expect mixed import styles in legacy scripts (example: `Problems/Combinations/test_MaxPalindromes.py` uses `from MaxPalindromes import ...`); preserve local style when making small fixes.

## Integration points and external dependencies
- Google AI: `AI/GoogleAI.py` requires `GOOGLE_API_KEY`; currently uses hardcoded absolute image paths (machine-specific). Prefer parameterizing paths/env vars in new work.
- Azure AI Agents: `AI/Agent.py` uses `azure.ai.projects` + `DefaultAzureCredential` with a hardcoded project endpoint; prefer env/config-driven endpoints and credentials in new work.
- Spark: scripts assume local Spark (`master("local[*]")`) and direct DataFrame construction utilities.
- Logging config expects YAML schema with `logger_type`, `buffer_size`, and sink definitions (`LLD/LoggerModule/logger/config_reader.py`).

## Editing guardrails for agents
- Check for top-level executable code before importing a module in tests/tools; many files are script-first.
- Avoid broad refactors across learning folders unless requested; treat each folder as an independent exercise area.
- Prefer targeted validation first (affected module/tests) before broad runs like full `uv run pytest`.
- When adding new code, keep it local to the target domain folder and include a small runnable example or test near that code.

## Specialized agent routing (`.github/agents/`)
- Use `.github/agents/README.md` as the quick index; use the agent files below for behavior details.
- `test-case-generator` - Create unit/integration tests with edge-case coverage; route for "write tests" requests.
- `build-validation-runner` - Run scoped validation with `uv` first, then broaden checks if needed.
- `git-commit-push-guard` - Handle safe commit/push flow (status, scoped commit, non-destructive push).
- `problem-solution-coach` - Solve/explain algorithm problems in `Problems/` with complexity and edge cases.
- `data-structure-implementer` - Implement/extend data structures in `DataStructures/` with practical tests.
- `bug-triage-debug` - Reproduce failures quickly and apply minimal-risk bug fixes.
- `python-cleanup-refactor` - Improve readability without behavior changes; keep refactors local.
- `system-design-simulator` - Work on simulations/prototypes in `SystemDesign/` and `LLD/`.
- `logger-variant-boundary` - Make logging changes while keeping `LLD/LoggerModule/logger/` and `Utils/` variants isolated.
- `ai-genai-experiments` - Build safe, parameterized Google GenAI scripts in `AI/`.
- `pyspark-local-jobs` - Implement readable local Spark jobs and DataFrame transforms in `PySpark/`.
- `pandas-script-analyst` - Improve dataframe workflows in `Pandas/` with explicit null/type handling.
- Maintenance: whenever a new `*.agent.md` is added, update this section and `.github/agents/README.md` together.
