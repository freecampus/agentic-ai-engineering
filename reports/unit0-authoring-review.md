# Unit 0 authoring and validation record

**Date:** 2026-09-19. **State:** authored, technically checked, awaiting
independent review; **not published or marked implemented**. Authoring was
AI-assisted. No independent reviewer is claimed. Source baseline:
`62b81f268eddccd1dfa1ccba5957c195eaff4084`; the working-tree artifacts
identified below are the review candidate, not a claimed new commit.

## 1. Scope and publication boundary

Five substantive lessons and **Prove the Lab Is Ready** now exist at the six
catalog paths under
`docs/courses/agentic-ai-engineering/units/launch-agent-lab/`. Each has a
concrete scenario, prerequisites/time/environment, opening questions, prediction
and controlled runs, failures, three two-question checkpoints, independent
acceptance checks, hidden help/solutions, evidence guidance, transfer, and
primary references. The challenge includes an actual broken notebook fixture and
CLI starter, exactly three progressive hints, a seven-case fresh-process
checker, and a retrospective.

There are 18 new quiz payloads and 36 questions. Package question banks and QMD
payloads are checked for exact agreement. The overview now describes the real
scenario, vocabulary, environment, stopping points, and draft challenge without
linking unreleased lesson routes.

No catalog IDs, outcomes, sequence, or counts changed: 25 units, 101 planned
lessons, 25 planned challenges; **zero published lessons/challenges**.
Completion remains disabled. All six authored activities use `draft: true` and
`content_status: draft`. They are excluded from public notebook export and
rendered as empty, unlinked Quarto drafts in normal builds. The review profile
uses a different output directory, sidebar, and explicit export flag. Drafts do
not advertise unavailable public Colab links. No deployment or commit was made.

The local plan records reflect `in_review`, not `implemented`. Local plans
remain ignored and optional; none is required by CI, notebooks, or either site
build.

## 2. Reusable implementation and observed negative cases

- `lab.py`: explicit `{"result": integer}` tool envelope with optional trusted
  tool injection. Ordinary smoke output stays byte-for-data equivalent to its
  existing JSON fixture. Missing/wrong fields, extra fields, strings, booleans,
  and non-mappings fail before observation. Unsupported names never invoke the
  injected tool. Unexpected tool exceptions propagate. A well-shaped wrong
  integer can still pass the schema; tests and instruction explicitly show this.
- `unit0.py`: bounded read-only synthetic lookup, exact task-file loading, and a
  shareable input/environment identity. Read spies verify permissions and budget
  before access. Missing input produces an actionable error, not a replacement.
- `launch_project.py` and `fixtures/launch_project.json`: refuse to overwrite an
  existing exercise directory; reproduce stale output and the CLI's hidden-cwd
  defect. The QMD CLI solution passes ordinary, zero, changed-operand, boolean,
  string, extra-field, and missing-file checks. Cached-answer and coercion
  mutations are rejected independently.
- Hidden QMD solutions are tested separately. Expected original failures include
  wrong result envelope, missing structured lookup evidence, coerced boolean
  input, cached notebook answer, and relative-file lookup from another
  directory. No unsafe shell/evaluation suggestion is executed.
- Notebook export preserves complete hidden solution blocks as collapsed
  Markdown, rather than silently running solutions during Run All. Intentional
  editable failures elsewhere and offline quiz practice remain covered by
  regression tests.

These are trusted in-process examples and inspected learner-code executions, not
security sandboxes. The project checker supplies the already imported package's
path to subprocesses; passing it **does not establish a local installation**.
The decision budget is not a timeout; the checker separately uses a ten-second
subprocess timeout. No service credentials, paid calls, model weights, or GPUs
were used.

## 3. Technical validation actually performed

Environment: Linux, CPython **3.14.7**, Poetry **2.4.3**, Conda CLI **24.11.2**,
Quarto **1.9.38**, package **0.1.0**. Python and Poetry resolve inside the
activated `fc-agentic` Conda prefix. The setup specification selects Python
3.12; that fresh setup and other supported Python/OS combinations were **not**
recreated here.

| Command/check                                                                                                                                                               | Observed result                                                                                                                                                                                     |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python scripts/check_environment.py`                                                                                                                                       | Passed in the actual activated environment.                                                                                                                                                         |
| `poetry check --lock --strict`                                                                                                                                              | Passed. No dependency or lockfile edits made.                                                                                                                                                       |
| `poetry run pytest -q tests/test_lab.py tests/test_environment.py tests/test_unit0.py tests/test_notebooks.py tests/test_learning_experience.py tests/test_site_outputs.py` | **135 passed**.                                                                                                                                                                                     |
| `poetry run pytest -q`                                                                                                                                                      | **204 passed, 1 pre-existing failure**, described below.                                                                                                                                            |
| `poetry run ruff check src tests scripts`                                                                                                                                   | Passed.                                                                                                                                                                                             |
| `poetry run ruff format --check src tests scripts`                                                                                                                          | Passed.                                                                                                                                                                                             |
| `poetry run mypy src`                                                                                                                                                       | Passed for all 8 package source files.                                                                                                                                                              |
| `poetry build`                                                                                                                                                              | Wheel and sdist built. New fixture assets present; isolated wheel import/smoke and challenge quiz-bank load passed.                                                                                 |
| `poetry run makim docs.build`                                                                                                                                               | 36 non-draft HTML pages + 30 notebooks verified; six draft HTML routes are empty and unlinked.                                                                                                      |
| `poetry run makim docs.review`                                                                                                                                              | 42 review HTML pages + 36 notebooks verified, including all six new activities.                                                                                                                     |
| `scripts/check_site.py`, normal and `--review`                                                                                                                              | Local references and executable OJS payload counts passed. Synthetic regression tests reject leaked draft notebooks/content and unavailable Colab links.                                            |
| Six notebook exports, cell by cell in separate `python -I -S` processes                                                                                                     | Passed from temporary working directories without ambient site-package imports. Package setup supplies the course source. All examples are tested without automatically executing hidden solutions. |
| Six QMD worked-example/solution sequences, independently of Run All                                                                                                         | Passed in fresh isolated processes; the challenge CLI solution is tested as its own file/process.                                                                                                   |
| Existing smoke notebook and Node browser-progress tests                                                                                                                     | Passed in the suite.                                                                                                                                                                                |

The full-suite failure is
`tests/test_tooling.py::test_poetry_metadata_preserves_package_extras_and_build_assets`
at line 23. It expects `docs` under `[dependency-groups]`; current metadata has
only `dev` there and an optional legacy Poetry `docs` group. The **same failure
was reproduced using the baseline commit's test and pyproject**, copied with
`git show HEAD:<path>` into a local scratch directory. Neither file was changed
to hide it. This remains a maintainer/tooling follow-up, not a Unit 0
regression.

Quarto continues to warn about OJS block-count/line-number reporting (also seen
on the pre-existing smoke page). Both builds finish, and all expected executable
renderer payloads are present. That structural check is not a browser
interaction or accessibility review.

## 4. Checks not performed or not completed

- **Actual Jupyter kernel execution was attempted but could not start.**
  NBClient 0.11.0 with ipykernel 7.3.0 failed before the first cell because the
  sandbox denies socket creation:
  `PermissionError: [Errno 1] Operation not permitted`. No restriction bypass
  was attempted. The successful fresh-Python cell tests are distinct evidence
  and are not labeled a successful Jupyter/Colab run.
- No desktop/mobile browser binary was available. Keyboard-only navigation,
  focus/feedback, narrow-screen layout, and rendered hidden-solution/quiz parity
  need manual browser review. No screenshots or visual-review success invented.
- No independent teaching reviewer, learner pilot, rubric score, or validated
  timing estimate. The original unit range remains 10–16 hours, including the
  90–180 minute challenge, pending pilot calibration.
- No fresh registry installation, Windows/macOS setup, hosted Colab execution,
  or full supported-Python matrix was performed. The existing Conda environment
  was checked; it was not destroyed or recreated.

These omissions prevent claiming the unit meets its full definition of done.

## 5. Independent review handoff

Run `poetry run makim docs.review` in the activated environment, then serve
`docs/_review` over loopback HTTP as described in README. Start at Lesson 0.1
and use the review sidebar. The matching `.ipynb` files are under the review
output's `notebooks/courses/agentic-ai-engineering/units/launch-agent-lab/`
directory. Normal public builds and the deployment workflow never use `_review`.

- [ ] Inspect every explanation, misconception distractor, scope boundary, and
      prerequisite; independently score the teaching rubric and resolve
      findings.
- [ ] Attempt each lab before opening its solution; check the unfamiliar
      transfers without leaking their answers into the prompts.
- [ ] Start a real fresh Jupyter/Colab kernel and run each exported notebook,
      then separately attempt and verify the learner lab. NBClient may automate
      kernel execution where installed and local socket creation is permitted;
      see its
      [primary execution documentation](https://nbclient.readthedocs.io/en/latest/client.html).
- [ ] Test three checkpoints per activity with keyboard only and with a narrow
      viewport; inspect focus, Next/Previous, feedback, score, and notebook
      parity.
- [ ] Confirm a fresh locked install and the actual OS/shell path-with-spaces
      cases.
- [ ] Resolve the baseline metadata test independently of teaching acceptance.
- [ ] After review, coordinate publication: remove draft flags, set catalog/QMD
      availability, update home counts/metadata/navigation, and reconcile
      explicit progress IDs. Do not enable whole-course completion before its
      full rule exists. Update local plan records only with actual
      reviewer/evidence details.

## 6. Sources, licenses, and evidence identities

Primary references were inspected on 2026-09-19: Python dataclasses, exceptions,
pathlib, sys arguments and subprocess; pytest assertions; Colab FAQ; IPython
magics; Conda environment management; Poetry installation/configuration; Ruff;
MyPy; Quarto drafts/conditional content; and NBClient execution. Direct,
claim-specific links appear in the QMD sources (NBClient above). Their example
code was not copied wholesale. The source implementation and root `LICENSE` were
inspected: original course code, synthetic data, quiz questions, and the seeded
notebook/project are BSD-3-Clause. No third-party dataset or model license is
implied. The deliberately fake citation in Lesson 0.3 is labeled a fixture, not
included as authority.

The following SHA-256 identities delimit the authored teaching/runtime
candidate. They do not prove correctness; rerun validation and update this
record after edits.

| Artifact                                                                               | SHA-256                                                            |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `docs/courses/agentic-ai-engineering/units/launch-agent-lab/build-local-workspace.qmd` | `51450b79d8d581e2c06a49a45bb0ae90bc743ac48af7afec9efca521504e0031` |
| `docs/courses/agentic-ai-engineering/units/launch-agent-lab/challenge.qmd`             | `411c1f51424fe7af37e9b17ac1ddf524168206eee6c9a8a97d3123d1ab9f2e00` |
| `docs/courses/agentic-ai-engineering/units/launch-agent-lab/index.qmd`                 | `2fe930ff5cc57a8f4897a21c3837c77784ea342df5d2b47f52985aa5599eb775` |
| `docs/courses/agentic-ai-engineering/units/launch-agent-lab/learn-with-evidence.qmd`   | `0699c00613d7988a681228d6021339cca3c95f87dd5fcd08abe96c17ac2aafd8` |
| `docs/courses/agentic-ai-engineering/units/launch-agent-lab/meet-a-tiny-agent.qmd`     | `e675e1bf32c40d091a830675b9cbee67a133559d41a4d88f446fb49c808b5e7f` |
| `docs/courses/agentic-ai-engineering/units/launch-agent-lab/use-ai-responsibly.qmd`    | `b2c87d3b509c6ef775d40283b9df638ed20a7db6c3058881c4138e40eb860673` |
| `docs/courses/agentic-ai-engineering/units/launch-agent-lab/work-in-notebooks.qmd`     | `ebc9390ddabedf09c4dd1a5b246c071211d820639fe2a13b519ad083910239ab` |
| `src/freecampus_agents/lab.py`                                                         | `1106cb7946d0ce2c413c0eb53f4bd8a924450e2d3cb6de31879979f196ceb423` |
| `src/freecampus_agents/unit0.py`                                                       | `91d6f3c8cd20d1948a9aa3c52b166eccd0d07d5c3294c34e5a8044fd4e78a3e8` |
| `src/freecampus_agents/launch_project.py`                                              | `e362f495bec3a658d1b92e7223a5b5e257110d8ff8da4b94fe8c3a4d9cdc9fbf` |
| `src/freecampus_agents/unit0_quizzes.py`                                               | `a476d3a3086b4f35e01afb1ad802ee8e63ca7e00bf9ec5b6ba8a2fea29434726` |
| `src/freecampus_agents/fixtures/launch_project.json`                                   | `a884110950fe9bcade63472dda940fed11b19cbd6e6232f8c473c53d1488a231` |
| `src/freecampus_agents/fixtures/unit0_quizzes.json`                                    | `1fda1947373e99273f5701b6fec08dc8f8d63ce4988f3f704eae4f538bec378e` |
