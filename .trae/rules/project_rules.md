# Project Rules – Python

## 🐍 Code Style
- Follow **PEP 8** strictly.
- Use **Black** for formatting and **isort** for imports.
- Use **snake_case** for functions and variables, **PascalCase** for classes, and **UPPER_CASE** for constants.
- Keep functions small and focused (≤ 30 lines recommended).
- Add **docstrings** to all public functions, classes, and modules (Google-style).
- Use type hints (`mypy` compatible) for all functions and class methods.

## 📦 Dependencies
- Use `uv` for dependency management (fast replacement for pip).
- All dependencies must be declared in `pyproject.toml`.
- Run `uv pip sync` before running tests or building.
- Pin dependencies to **compatible latest versions** (e.g., `requests^2.32`).

## 🧪 Testing
- Use **pytest** for testing.
- Place tests under `tests/` with file naming: `test_*.py`.
- Achieve and maintain at least **80% coverage** (use `pytest --cov`).
- Write both **unit tests** and **integration tests** for critical modules.
- Run `pytest -q` locally before every commit.

## 🛠️ Tooling
- Format code: `uv run black src/`
- Sort imports: `uv run isort src/`
- Type-check: `uv run mypy src/`
- Lint: `uv run flake8 src/`
- Run all checks:  
  ```bash
  uv run black src/ && uv run isort src/ && uv run mypy src/ && uv run flake8 src/ && pytest

## Model

When reasoning through a task, prioritize direct execution over exhaustive planning. If a plan exceeds 5 steps, execute the first 3 steps immediately and then pause for feedback.
