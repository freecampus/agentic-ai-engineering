# FreeCampus Agentic AI Engineering

A project-driven course for learners with **project-ready Python** who want to
build, evaluate, defend, and operate agentic systems—and know when not to use
one.

**Status: infrastructure scaffold; curriculum in development.** The planned
course contains 25 units, 101 lessons, 25 unit challenges, four numbered
milestone projects, and one six-stage capstone. No content lessons or unit
challenges are released yet. Available now: the course map, 25 unit previews,
readiness guidance, project outlines, and an executable deterministic smoke lab.

Unit 0 now has five complete lesson drafts and a guided challenge, including
offline labs, 36 checkpoint questions, and reproducible failure/repair fixtures.
They await independent teaching/accessibility review and are not counted as
published lessons. See the
[Unit 0 authoring report](reports/unit0-authoring-review.md).

Unit 1 now has four detailed lesson drafts and **De-Agentify an Overbuilt
System**, with theory, offline experiments, 45 checkpoint questions, hidden
worked solutions, and a costed architecture decision. These also remain
unpublished review drafts. See the
[Unit 1 authoring report](reports/unit1-authoring-review.md).

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

Use **uv** for Python and **Just** for project commands. Install Git,
[uv](https://docs.astral.sh/uv/getting-started/installation/),
[Just](https://just.systems/man/en/chapter_4.html), and Node.js 24 (for Prettier),
then run these commands from the repository root. Quarto is installed with the
docs dependency group.

```bash
uv sync --locked --all-groups --all-extras  # First setup and after dependency changes
just environment
uv run --locked python -m freecampus_agents.lab
just lint
just test
just package
just docs
just preview
just hooks  # Optional: install Git pre-commit hooks
```

uv reads the Python version from `.python-version`, creates `.venv`, and installs
the exact versions in the tracked `uv.lock`. Use `uv add` to add a runtime
dependency, `uv add --group dev` for a development dependency, and
`uv lock --upgrade-package PACKAGE` when deliberately updating one dependency.
Run `uv sync --locked --all-groups --all-extras` after changing dependencies.
The environment check confirms commands are using this checkout's uv environment.

Just recipes are listed by running `just`; recipes such as `just docs`,
`just test`, and `just ci` call the project tools through uv. CI checks Python
3.10, 3.12, and 3.14. Pre-commit hooks use `language: system` and call tools via
`uv run`; the pinned Prettier command uses Node.js and needs registry access the
first time it runs. See [uv projects](https://docs.astral.sh/uv/guides/projects/)
and [pre-commit system hooks](https://pre-commit.com/#system) for details.

The core package has no runtime dependencies; notebook widgets are an extra.
Hosted Colab notebooks use their supplied runtime and bundled course package;
they do not require a local uv environment.

### Lockfile validation and release evidence

Commit `uv.lock` so local setups and CI install the same resolved dependencies.
`uv lock --check` verifies that project metadata and the lockfile agree;
`uv sync --locked` refuses to update a stale lock silently. Update the lock with
`uv lock` after intentional dependency changes and review the resulting diff.
A valid lock alone does not prove clean installation or cross-platform
compatibility.

## Website and notebooks

Quarto execution is disabled globally. `just docs` renders the
site, exports notebooks, and checks that every expected HTML page and notebook
exists. Published Colab links target this repository's `gh-pages` branch; they
become usable after deployment. Do not edit `docs/_site` by hand.

The smoke notebook embeds the small course package from this checkout, including
its fixture. It runs without downloading a package or contacting a provider.
Browser OJS quizzes become offline Markdown questions with hidden answers in
notebook exports. Overview notebooks remain clearly labeled orientation
material.

### Review Units 0–1 without publishing them

```bash
just environment
just review
```

Open
`docs/_review/courses/agentic-ai-engineering/units/launch-agent-lab/meet-a-tiny-agent.html`
using a local web server (OJS modules require HTTP), for example
`python -m http.server 8000 --bind 127.0.0.1 --directory docs/_review`. The
review sidebar contains both units' lessons and Unit Challenges. Matching Unit 0
notebooks are under
`docs/_review/notebooks/courses/agentic-ai-engineering/units/launch-agent-lab/`.
Upload an exported notebook manually to Colab or open it in Jupyter. Hidden
solutions remain collapsed Markdown, not code executed by Run All.

For Unit 1, start at
`docs/_review/courses/agentic-ai-engineering/units/choose-agent-architecture/separate-automation-workflows-and-agents.html`.
Its five notebooks are under
`docs/_review/notebooks/courses/agentic-ai-engineering/units/choose-agent-architecture/`
(alongside the overview notebook).

Normal `docs.build` omits draft content and notebook exports. The separate
review output is ignored and never deployed by the docs workflow. Do not publish
it as an alternative way to bypass review. Completion and public Colab launch
links remain disabled on drafts. `just clean` removes both generated sites.

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
just plan-refresh
just plan-check
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
just environment
just lint
just test
just package
just docs
git diff --check
just clean
```

Cleanup removes known generated sites, caches, and build outputs, not `.venv` or
other virtual environments. CI validates pull requests. The docs workflow
publishes only main pushes or manual dispatches; package publishing remains
disabled.
