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
- [Draft curriculum specification](PLAN-DETAILS.md)

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

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and use
Python 3.12 for the default workspace. The package supports Python 3.10 and
later; `.python-version` selects the development baseline.

```bash
uv sync --all-extras --group docs
uv run python -m freecampus_agents.lab
uv run makim tests.linter
uv run makim tests.unit
uv build
uv run makim docs.build
uv run makim docs.preview
```

These commands work from the repository root without activating the environment.
The optional `conda.yaml` bootstraps Python, uv, and Node; it does not manage
course package dependencies. Node is used for browser-behavior regression tests.
Core package installation has no runtime dependencies; notebook widgets are an
extra.

### Lockfile bootstrap still required

The migration environment had no package-registry network access, so **`uv.lock`
has not been generated**. Top-level version bounds are declared, but transitive
reproducibility is not yet established. Before a reproducible release:

1. Run `uv lock` with registry access and inspect the resulting lockfile.
2. Include `uv.lock` in version control.
3. Change workflow installation commands to `uv sync --locked ...`.
4. Validate with `uv lock --check` and clean installations on supported
   platforms.

CI currently resolves dependencies during installation rather than pretending a
missing lockfile exists. See
[uv's project documentation](https://docs.astral.sh/uv/guides/projects/) for
lockfile and synchronization behavior.

## Website and notebooks

Quarto execution is disabled globally. `uv run makim docs.build` renders the
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

`PLAN.md` stays ignored as local implementation planning. `PLAN-DETAILS.md` is
the tracked draft specification. The suggested nested package tree in that draft
is implemented with repository-level `src/` and `tests/` to retain standard
packaging.

## Validation and cleanup

```bash
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src
uv build
uv run makim docs.build
git diff --check
uv run makim clean.tmp
```

Cleanup removes generated sites, caches, and build outputs, not the virtual
environment. CI validates pull requests. The docs workflow publishes only main
pushes or manual dispatches; package publishing remains disabled.
