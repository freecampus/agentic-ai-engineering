# Unit 1 authoring and execution report

Date: 2026-09-21. Unit: `choose-agent-architecture` — **Decide Whether a Problem
Needs an Agent**. This is an authoring/self-check report, not an independent
teaching, accessibility, security, or release approval.

## 1. Scope and publication state

Authored four substantive lessons and one 90–180 minute guided challenge:

| Activity                                   | Theory and concepts                                                                                               | Practical evidence                                                                                                                                                                         |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Separate Automation, Workflows, and Agents | Definitions, authority, feedback, DAGs, state machines, fixed workflows, controller boundaries                    | Executable DAG/cycle and transition-table examples; same-input query/workflow/agent traces; zero-decision replacement and classification dossier                                           |
| Model the Agent–Environment Loop           | State versus observation versus belief; transition/observation functions; cost, objectives, terminal outcomes     | Blocked grid and read-only tool worlds; missing-observation fixture; chained transition checker; terminal and injected-cost failures                                                       |
| Bound Autonomy with Task Contracts         | Scoped autonomy; structural versus semantic validation; least privilege; approval, deadlines, budgets, escalation | JSON Schema artifact plus limited stdlib validator; allow/deny/confirm/stop table; dispatch spies; invalid contracts, expired approval, zero allowance, failed-effect accounting           |
| Choose the Simplest Adequate Architecture  | Adequacy before cost; failure opportunities; conditional reliability arithmetic; qualification procedure; ADRs    | Five candidates on identical fixtures; independent literal oracles; synthetic-cost sensitivity; explicit no-go; rejected alternatives and revisit triggers                                 |
| De-Agentify an Overbuilt System            | Integration of the four lessons without advanced frameworks                                                       | Five-controller baseline, editable starter, two defective shortcuts, progressive ordinary/boundary/adversarial checks, three hint levels, hidden solution, debugging record, retrospective |

Each activity has three shared-renderer checkpoints with three questions each:
**45 original questions**, balanced answer positions and package/QMD parity. The
four lessons each state opening questions, prerequisites, time, environment,
outcome, evidence, failure diagnosis, acceptance criteria, and transfer work.
All examples use synthetic data and standard-library fake components, not live
models. A local read is not semantic retrieval; a fake policy is not an LLM; a
dispatch guard is not a sandbox; a fixture cost is not billing or latency.

The overview accurately describes the authored-but-unreleased state. Review-only
navigation includes both Units 0 and 1. Catalog IDs, outcome mappings, unit
count, lesson count, and challenge count are unchanged. The five new assessable
sources have `draft: true` and `content_status: draft`; catalog publication
remains `planned`, with **zero released lessons and challenges**. No public
navigation links to these drafts. Completion and public Colab launch links
remain disabled.

The unit remains **in review**, not implemented under the full editorial
definition of done. Effort remains 8–14 hours, including the 90–180 minute
challenge, pending pilot calibration. This work does not introduce OpenClaw,
Hermes, a provider SDK, a GPU dependency, or a new framework prerequisite.

## 2. Reusable code and independent assertions

- `src/freecampus_agents/architecture.py`: exact-key query, deliberately stale
  rule, fixed two-stage fake-model workflow, bounded feedback controller, and
  five separately initialized but identically scripted controllers. Shared
  allowlists/budgets and observed events make attempts countable.
- `src/freecampus_agents/environments.py`: immutable grid/tool transition
  records and an observation-only position update. Missing evidence does not
  become inaccessible ground truth.
- `src/freecampus_agents/contracts.py`: this course record's structural and
  cross-field validator, scoped decisions, and a synchronous dispatch gate.
  Approval records, time inputs, callbacks, and Python source are trusted. This
  does not implement authenticated approval, distributed reservations, durable
  replay prevention, or process isolation.
- `fixtures/unit1_requests.json`: four development and ten qualification cases
  with separately authored literal replies, group labels, source updates,
  outages, and untrusted notes. Candidates never receive case IDs or expected
  replies. Qualification is public and held out only by procedure; reuse is
  explicitly disclosed as regression evidence, not fresh held-out evaluation.
- `fixtures/unit1_contract.schema.json`: draft-2020-12 structural documentation.
  The Python validator is intentionally limited and somewhat stricter (for
  example, actual integer objects and nonblank text); no general JSON Schema
  conformance is claimed.
- `fixtures/unit1_quizzes.json` and `unit1_quizzes.py`: reusable validated quiz
  models matching the canonical QMD payloads.
- `tests/test_unit1.py`: literal ordinary results; changed source and outage
  cases; scope/approval/clock boundaries; no effects before authorization;
  attempted-work accounting; terminal failures; missing observations; invalid
  budgets/contracts; source-bank parity; and challenge publication barriers.

The worked challenge passes all ten qualification output contracts and the
narrow observed-event safety gate with zero decisions/five total reads, versus
75 decisions/25 reads for the original. Under uniform case weights and prices of
five units per decision and one per read, the assumed means are **0.5 versus
40**. These finite deterministic observations do not establish real-model
capability, production reliability, injection resistance, or a guaranteed
financial saving.

## 3. Executed checks

Environment: actual activated Conda `fc-agentic`, Python **3.14.7**, Poetry
**2.4.3**, Quarto **1.9.38**. `python scripts/check_environment.py` confirms
that Python and Poetry resolve inside the Conda prefix. The repository's local
setup specification still requests Python 3.12; no claim of a new 3.12
installation is made. No dependency metadata, lockfile, or CI workflow was
changed.

| Check                                                | Result                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------- |
| Environment guard; `poetry check --lock --strict`    | Passed                                                          |
| Focused Unit 1/notebook/curriculum/site-output suite | 96 passed                                                       |
| Full `poetry run pytest -q`                          | **263 passed, 1 pre-existing tooling failure**                  |
| `poetry run ruff check src tests scripts`            | Passed                                                          |
| `poetry run ruff format --check src tests scripts`   | Passed; 30 files                                                |
| `poetry run mypy src`                                | Passed; 12 source files                                         |
| `poetry build`                                       | Wheel and sdist built                                           |
| `poetry run makim docs.build`                        | 30 public notebooks; 66 expected HTML/notebook outputs verified |
| `poetry run makim docs.review`                       | 41 review notebooks; 88 expected HTML/notebook outputs verified |

The notebook regressions cover all five new activities, earlier Unit 0 drafts,
and the smoke resource. Each new export passes notebook-schema validation and
runs its code cells separately in a **fresh `python -I -S` process** with no
site packages. The embedded checkout package supplies its own imports and
fixtures. Hidden solutions remain collapsed Markdown during Run All and are
executed separately from canonical source by another regression. Quiz text,
explanations, numbered headings, and draft notices survive export. The test
harness now sends large embedded scripts over stdin instead of a `-c` argument,
avoiding platform argument-size limits as the source bundle grows.

The full-suite failure is
`tests/test_tooling.py::test_poetry_metadata_preserves_package_extras_and_build_assets`:
it expects `dependency-groups` to contain `dev` and `docs`, but the unchanged
project file contains `dev` plus the optional legacy Poetry docs group.
Reproduced using **both files copied from local `HEAD`** into an ignored scratch
directory; that isolated baseline test also fails at the same assertion. Neither
expectation nor dependency metadata was changed to hide it. Lock consistency and
package build pass, but they do not resolve this existing CI assertion.

Quarto reports an existing OJS block-count/line-number warning, including on the
smoke page. Both builds complete and the output checker finds all three
executable shared-renderer payloads on every new activity. HTML inspection also
finds draft identity, hidden challenge completion, and the Mermaid diagram.
Those are structural checks, not evidence of keyboard or visual usability.

## 4. Execution and review limitations

- **Real Jupyter execution attempted but not completed.** A Unit 1 notebook was
  passed to NBClient using the existing Python kernel specification. Startup
  failed before execution with
  `PermissionError: [Errno 1] Operation not permitted` during local
  interface/socket discovery. No restriction bypass was attempted. Fresh-Python
  cell execution is separately reported above and must not be described as a
  successful Jupyter or hosted Colab run.
- No browser tool or desktop browser binary was available. Narrow/desktop
  layout, keyboard navigation, Next/Previous behavior, feedback announcements,
  focus, and diagram readability need an actual browser/accessibility review.
- No independent technical or teaching reviewer, scored editorial rubric,
  learner pilot, or calibrated timing study. Author tests are not independent
  instructional validation.
- No fresh registry installation, supported-OS/Python matrix, hosted Colab run,
  live-provider evaluation, security audit, or production traffic/cost study.
- The schema describes the supplied structural shape, not a
  standards-conformance test suite. Fixture source integrity and trusted Python
  remain assumptions.

These limitations prevent marking the unit implemented or publishing it as a
released assessment.

## 5. Review handoff

Run `poetry run makim docs.review` inside the checked Conda environment. Serve
`docs/_review` over local HTTP as described in README; start at
`courses/agentic-ai-engineering/units/choose-agent-architecture/separate-automation-workflows-and-agents.html`.
The review sidebar orders the four lessons and challenge. Matching notebooks are
under
`notebooks/courses/agentic-ai-engineering/units/choose-agent-architecture/`. The
normal deployment workflow does not use this review output.

- [ ] Independently inspect concepts, terminology, prerequisite discipline,
      examples, distractors, code, finite-test claims, and safety limitations.
- [ ] Attempt every lab before opening its solution; test the unfamiliar
      transfers.
- [ ] In a permitted environment, execute every export with a genuinely fresh
      Jupyter/Colab kernel, then edit each starter and rerun the acceptance
      checks.
- [ ] Test all 15 checkpoints using keyboard-only and narrow/desktop viewports;
      inspect hidden solutions and notebook parity.
- [ ] Check the JSON shape/semantic distinction and delayed-approval
      limitations.
- [ ] Review the challenge's deliberately overbuilt baseline without treating it
      as a general claim against agents or multi-agent architectures.
- [ ] Pilot timings and independently score the editorial rubric. Record
      findings and rerun affected checks before approving publication.
- [ ] Resolve the pre-existing tooling assertion through separate dependency/CI
      maintenance, without weakening the underlying reproducibility requirement.

## 6. Primary references and provenance

Checked 2026-09-21; citations also appear at their point of use:

- Russell and Norvig, _Artificial Intelligence: A Modern Approach_,
  fourth-edition
  [agent chapter](https://aima.cs.berkeley.edu/4th-ed/pdfs/newchap02.pdf):
  terminology and the broad perception/action view; no textbook assets are
  copied.
- Anthropic,
  [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents),
  originally 2024-12-19: historical workflow/model-directed control distinction,
  not a current product recommendation.
- W3C, [SCXML recommendation](https://www.w3.org/TR/scxml/), 2015-09-01:
  transition/final-state vocabulary, not an introduced XML runtime.
- [Python graphlib](https://docs.python.org/3/library/graphlib.html),
  [functools.partial](https://docs.python.org/3/library/functools.html#functools.partial),
  and [dataclasses](https://docs.python.org/3/library/dataclasses.html): the
  standard-library mechanisms used in original examples.
- [JSON Schema Validation, draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation):
  structural vocabulary, distinct from the course's cross-field rules.
- [NIST least privilege](https://csrc.nist.gov/glossary/term/least_privilege): a
  principle, not certification of the supplied implementation.
- Michael Nygard,
  [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions),
  2011-11-15: lightweight decision records; the evidence fields are
  course-specific.

Stories, examples, fixtures, questions, solutions, and code are original
synthetic course material under the repository's BSD-3-Clause license. No
external diagrams, proprietary customer data, credentials, or authenticated
content are bundled.

## 7. Source fingerprints for review handoff

SHA-256 of the authored unit sources, supporting code/data, and focused tests. A
later source change requires rechecking affected evidence.

```text
39a150d7804a1722318117bd138ff9e256c2202a0bb4be8158c3dba8cd51ecd3  docs/courses/agentic-ai-engineering/units/choose-agent-architecture/bound-autonomy-with-task-contracts.qmd
e0f3d537610209c1dafbc47b40b08b9d8980cdfa532be8e35162c98b304b4572  docs/courses/agentic-ai-engineering/units/choose-agent-architecture/challenge.qmd
efbed3b01a613180e00d88a33b5d84f00d043c773e0ec91be4e360a6cb5636de  docs/courses/agentic-ai-engineering/units/choose-agent-architecture/choose-the-simplest-adequate-architecture.qmd
69d48dea8e929b306d66d3b5e320df62bbc5c54368de4b305125dec7a06d540b  docs/courses/agentic-ai-engineering/units/choose-agent-architecture/index.qmd
623d1a7f743d8c3630ff142a762f7195e5b4c4a8555273b3ba4fbab0a6dd585b  docs/courses/agentic-ai-engineering/units/choose-agent-architecture/model-the-agent-environment-loop.qmd
f3b037a7a12ddcc09b4c75b5cdfad86859201d651bb484981a303c20d6c2373a  docs/courses/agentic-ai-engineering/units/choose-agent-architecture/separate-automation-workflows-and-agents.qmd
b9925160274a638b8f7afc23dd55150499b92b7f764a0d30c633a2370df883a6  src/freecampus_agents/architecture.py
a5a0244ecab619d21db8e14364e2425e8dae350b9ba36b670312d70073f3d8df  src/freecampus_agents/contracts.py
8e2edcc2f9f0f481372d837b44e93954cb63b7dc020b1af57cbcf68a6227f9f3  src/freecampus_agents/environments.py
eaef43e6a0891d7fbaca7fedd581b9a48533e191d10c20dec3e8d5b51e6516ce  src/freecampus_agents/unit1_quizzes.py
0da263cbd59acea6380a36255180844d8000a5b95fb462510f35b09d5d3be08f  src/freecampus_agents/fixtures/unit1_contract.schema.json
fdc209ab14cf48c3d0ea367b4fdebe266690c48bd696daaee3b9b3a19778138a  src/freecampus_agents/fixtures/unit1_quizzes.json
0ee161ed9d062a0d429411eb225815b69e105e7513c2086f647d91fa748334ff  src/freecampus_agents/fixtures/unit1_requests.json
706fd897c6a06626dfe3dc1beebaa891ec07143f6d66c2c1e3702069cb0f7ab1  tests/test_unit1.py
```
