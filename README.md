# FreeCampus Agentic AI Engineering

A project-driven course for learners with **project-ready Python** who want to
build, evaluate, defend, and operate agentic systems—and know when not to use
one.

**Status: infrastructure scaffold; curriculum in development.** The planned
course contains 25 units, 101 lessons, 25 unit challenges, four numbered
milestone projects, and one six-stage capstone. No content lessons or unit
challenges are released yet. Available now: the course map, 25 unit previews,
readiness guidance, project outlines, and an executable deterministic smoke lab.

## Explore the course

- [Website source](docs/index.qmd)
- [Complete curriculum map](docs/courses/agentic-ai-engineering/index.qmd)
- [Python readiness](docs/courses/agentic-ai-engineering/readiness.qmd)
- [Unit 0: Launch a Reproducible Agent Engineering Lab](docs/courses/agentic-ai-engineering/units/launch-agent-lab/index.qmd)
- [Offline smoke lab](docs/resources/agent-lab.qmd)
- [Milestone outlines](docs/courses/agentic-ai-engineering/projects/index.qmd)
- [Capstone outline](docs/courses/agentic-ai-engineering/capstone/index.qmd)
- [Contributor workflow](docs/resources/contributing.qmd)

The learning cycle is **Specify → Predict → Run → Inspect → Explain → Modify →
Evaluate → Attack → Record**. Start with deterministic fake models and
non-agentic baselines. Add model variability, tools, memory, protocols, and
autonomy only with observable tests, controlled permissions, and evidence of
value.

The core route requires no paid inference. Network-based activities will have
recorded fixtures; hardware-heavy and paid-provider comparisons remain optional.
The smoke runtime uses only Python's standard library and makes no network
calls.

## Local development

**Conda + Poetry are required for development and CI.** Install Conda (for
example, Miniforge), then run the following from the repository root. Conda owns
the environment and supplies Python 3.12, Poetry 2.4+ within the 2.x series,
Node.js, and pip. Poetry installs the project's Python dependencies directly
into that activated Conda environment—not a separate virtual environment.

```bash
conda env create -f conda.yaml  # First setup only
conda activate fc-agentic
python scripts/check_environment.py
poetry install --all-extras --with docs
python scripts/check_environment.py
poetry run python -m freecampus_agents.lab
poetry run makim tests.linter
poetry run makim tests.unit
poetry build
poetry run makim docs.build
poetry run makim docs.preview
```

Activate `fc-agentic` in each new terminal; do not work in Conda's `base`
environment. Use a Conda-initialized terminal on Windows, macOS, or Linux. If
activation is unavailable, initialize your shell following
[Conda's environment guide](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html).
Set your editor's interpreter to this same Conda environment.

The shared `poetry.toml` disables virtualenv creation and in-project virtualenv
selection. The environment check rejects a nested Python venv, conflicting
Poetry settings, or Python/Poetry pointing outside the active Conda environment.
It runs before CI installation and developer validation tasks. Do not use
`poetry env use` or `python -m venv` here. Existing environment directories are
left untouched, not adopted for development.

Poetry may label the active Conda prefix as `VIRTUAL_ENV` inside `poetry run`.
The check verifies the real interpreter and Conda metadata, rather than treating
that label alone as evidence of a separate venv. Do not set it manually.

Use `poetry install`, not `poetry sync`: synchronization can remove Conda-owned
tooling outside the project dependency set. Both CI workflows use `conda.yaml`
with activated login shells; validation covers Python 3.10, 3.12, and 3.14. Node
supports browser tests and formatting. Pre-commit hooks use `language: system`
and Poetry-installed tools, not isolated hook environments; the pinned Prettier
command uses Conda's npm and needs registry access on its first run. See
[Poetry's environment settings](https://python-poetry.org/docs/configuration/#virtualenvscreate)
and [system hooks](https://pre-commit.com/#system) for those behaviors.

The core package has no runtime dependencies; notebook widgets are an extra.
Hosted Colab notebooks use their supplied runtime and bundled course package;
they do not require a local Conda installation.

### Lockfile bootstrap still required

The Poetry migration attempted `poetry lock`, but connections to PyPI failed, so
**`poetry.lock` has not been generated**. Top-level version bounds are declared,
but transitive reproducibility is not yet established. Before a reproducible
release:

1. Run `poetry lock` with registry access and inspect the resulting lockfile.
2. Include `poetry.lock` in version control; do not copy the other course's
   lock.
3. Add `poetry check --lock --strict` before installation in both CI workflows.
4. Validate clean installations using `poetry install --all-extras --with docs`
   on supported platforms. Installation uses the committed lockfile once
   present.

CI currently resolves dependencies during installation rather than pretending a
missing lockfile exists. See
[Poetry's basic usage](https://python-poetry.org/docs/basic-usage/) for lockfile
behavior and
[dependency groups](https://python-poetry.org/docs/managing-dependencies/) for
installation options.

## Website and notebooks

Quarto execution is disabled globally. `poetry run makim docs.build` renders the
site, exports notebooks, and checks that every expected HTML page and notebook
exists. Published Colab links target this repository's `gh-pages` branch; they
become usable after deployment. Do not edit `docs/_site` by hand.

The smoke notebook embeds the small course package from this checkout, including
its fixture. It runs without downloading a package or contacting a provider.
Browser OJS quizzes become offline Markdown questions with hidden answers in
notebook exports. Overview notebooks remain clearly labeled orientation
material.

Progress storage uses this course's own namespace and only explicit published
activity IDs. Progress is local and self-reported, not verified grading or a
certificate. Completion is disabled while the curriculum is planned.

## Structure and authoring

```text
PLAN*.md                                 # Optional local planning; ignored and absent in fresh checkouts
docs/courses/_catalog.yml                  # Canonical curriculum and publication status
docs/courses/agentic-ai-engineering/       # Course home, readiness, units, projects, capstone
docs/resources/                           # Smoke lab, journal, FAQ, contributor guidance
docs/_templates/                          # Unpublished authoring scaffolds
src/freecampus_agents/                    # Smoke runtime, synthetic fixtures, quiz helpers
scripts/                                 # Build, notebook export, output checks, cleanup
tests/                                   # Package and status-aware course invariants
```

Read [AGENTS.md](AGENTS.md) and the
[contributor guide](docs/resources/contributing.qmd) before authoring. Planned
lesson paths exist in the catalog, not as misleading placeholder lessons.
Publishing a lesson requires full instruction, quizzes, acceptance tests, clean
notebook execution, and synchronized metadata and outcomes.

All `PLAN*.md` files are **ignored local planning material**. They are not
distributed in a checkout and are not required for tests, CI, or documentation
builds. The tracked catalog, outcome map, and QMD sources define the public
curriculum. The package uses repository-level `src/` and `tests/`.

### Optional local development tracker

When you have a maintainer's local `PLAN-LESSONS.md`, it contains one milestone
per unit and one task per lesson, with detailed briefs and status/evidence
fields. Update status (`not_done`, `in_progress`, `in_review`, `implemented`, or
`blocked`), owner, date, and evidence as work advances. Then explicitly run:

```bash
poetry run makim plan.refresh
poetry run makim plan.check
```

These commands check the real local briefs, catalog alignment, records, and
dashboard. They report a missing plan as a local setup issue, not a CI failure,
and never create placeholders. Normal pytest runs test the validator with
synthetic fixtures, not your local plan; use `plan.check` to check that file.
Keep local backups/change notes because Git does not record ignored plans.

The dashboard is generated, not a second status store. Unit gates, capstone
stages, and course release readiness are counted separately. Implemented lessons
need reviewed execution, teaching, accessibility, and reference evidence;
existing previews and infrastructure do not count. Catalog publication status
and learner self-reported progress remain separate.

## Validation and cleanup

```bash
conda activate fc-agentic
python scripts/check_environment.py
poetry check --strict
poetry run pytest -q
poetry run ruff check src tests scripts
poetry run ruff format --check src tests scripts
poetry run mypy src
poetry build
poetry run makim docs.build
git diff --check
poetry run makim clean.tmp
```

Cleanup removes known generated sites, caches, and build outputs, not Conda or
legacy virtual environments. CI validates pull requests. The docs workflow
publishes only main pushes or manual dispatches; package publishing remains
disabled.
