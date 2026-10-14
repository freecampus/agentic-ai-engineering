# Use `just` to discover the shared project commands.
default:
    @just --list

# Install the complete locked development and documentation environment.
setup:
    uv sync --locked --all-groups --all-extras

# Check that the current Python process is the project uv environment.
environment:
    uv run --locked python scripts/check_environment.py

# Refresh the ignored local lesson-plan dashboard.
plan-refresh:
    uv run --locked python scripts/check_lesson_plan.py --refresh

# Check ignored local lesson-plan briefs and records.
plan-check:
    uv run --locked python scripts/check_lesson_plan.py

# Check formatting, lint, and types.
lint:
    uv run --locked ruff check src tests scripts
    uv run --locked ruff format --check src tests scripts
    uv run --locked mypy src

# Run the test suite.
test:
    uv run --locked pytest -q

# Build the Python distributions.
package:
    uv lock --check
    uv build

# Render the course and export Colab notebooks.
docs:
    uv run --locked --all-groups --all-extras python scripts/project.py docs

# Render review drafts into the private review output.
review:
    uv run --locked --all-groups --all-extras python scripts/project.py review

# Build and preview the Quarto site.
preview:
    uv run --locked --all-groups --all-extras python scripts/project.py preview

# Install this checkout's Git hooks.
hooks:
    uv run --locked pre-commit install

# Remove known generated files and caches.
clean:
    uv run --no-project python scripts/project.py clean

# Run lint, tests, package checks, site build, and notebook checks.
ci:
    uv run --locked --all-groups --all-extras python scripts/project.py all
