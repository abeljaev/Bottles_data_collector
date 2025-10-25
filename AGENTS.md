# Repository Guidelines

## Project Structure & Module Organization
- Core package in `src/collector/` with `app.py` (CLI and launch), `web_ui.py` (Gradio UI), `collector.py` (state + spec loading), `config.py` (YAML config), `export.py` (CSV helpers), `io_utils.py` (filesystem handling).
- Runtime settings live in `config.yaml`; class schemas in `states/*.yaml` define UI attributes and must stay in sync with dataset expectations.
- Captures land in `dataset/YYYYMMDD/` with `images/` and `meta/` subfolders; large exports go into `export_data/`.
- Dependency manifests are `pyproject.toml` and `uv.lock`; avoid editing `collector.egg-info` directly.

## Build, Test, and Development Commands
- `uv sync` — install or refresh the pinned environment (creates `.venv`).
- `uv run collector` — start the camera selector and Gradio UI (opens http://127.0.0.1:7860).
- `uv run python -m collector.app --config config.yaml` — bypass the entry script when debugging alternate configs.
- Without `uv`, activate `.venv` and run `python -m collector.app`.

## Coding Style & Naming Conventions
- Target Python 3.9+, 4-space indentation, module docstrings, and explicit type hints for public APIs.
- Follow `snake_case` for functions/variables, `PascalCase` for classes, and keep modules lowercase to match the existing layout.
- Use `loguru.logger` for structured logging and `rich` utilities for terminal UX; keep user-facing strings localized (current UI is Russian-first).

## Testing Guidelines
- Automated tests are pending; add new specs under `tests/` mirroring package structure (`tests/test_io_utils.py`, etc.) using `pytest`.
- Mock camera and filesystem calls so `uv run pytest` can run headless; include regression data under `tests/data/` if needed.
- Document any manual verification (e.g., sample capture + CSV export) in the PR description until the suite is established.

## Commit & Pull Request Guidelines
- History favors short sentence-case subjects (`Major refactoring: ...`); keep ≤72 characters and expand details in the body when necessary.
- Reference related issues, list highlights, and record how you tested (`uv run collector`, `uv run pytest`, manual export).
- PRs should describe UX implications, attach UI screenshots when Gradio layout changes, and note dataset/output impacts.
- Request review only after the app starts cleanly and new tests or manual checks pass.

## Configuration & Data Handling
- Do not commit personal captures from `dataset/` or generated CSVs in `export_data/`; scrub them before pushing.
- Update `config.yaml` cautiously—document changes that affect camera probing, class schemas, or export defaults.
