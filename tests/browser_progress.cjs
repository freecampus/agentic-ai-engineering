const vm = require("node:vm");
const assert = require("node:assert/strict");
const source = require("node:fs")
  .readFileSync("docs/_includes/course-ui.html", "utf8")
  .replace(/^<script>/, "")
  .replace(/<\/script>\n$/, "");
const key = "freecampus.agentic-ai-engineering.progress.v1";
function element() {
  return {
    hidden: true,
    textContent: "",
    style: {},
    attrs: {},
    listeners: {},
    classList: { toggle() {} },
    setAttribute(k, v) {
      this.attrs[k] = v;
    },
    addEventListener(k, f) {
      this.listeners[k] = f;
    },
    querySelector() {
      return null;
    },
  };
}
function run(metadata = {}, stored = null, blocked = false) {
  const header = element();
  header.dataset = {
    fcCourseId: "agentic-ai-engineering",
    fcCurriculumVersion: "1",
    fcCompletionRuleVersion: "1",
    fcContentStatus: "available",
    fcLessonId: "unit.lesson",
    fcLessonIds: "unit.lesson",
    fcChallengeIds: "unit.challenge",
    ...metadata,
  };
  const button = element(),
    challenge = element(),
    root = element(),
    status = element();
  const label = element(),
    value = element(),
    bar = element(),
    track = element();
  const pieces = {
    "[data-fc-progress-label]": label,
    "[data-fc-progress-value]": value,
    "[data-fc-progress-bar]": bar,
    "[data-fc-progress-track]": track,
  };
  root.querySelector = (s) => pieces[s] || null;
  const elements = {
    "#title-block-header": header,
    "[data-fc-complete]": button,
    "[data-fc-challenge-complete]": challenge,
    "[data-fc-lesson-progress]": root,
    "[data-fc-storage-status]": status,
  };
  let written = null;
  const sandbox = {
    document: {
      querySelector: (s) => elements[s] || null,
      querySelectorAll: () => [],
    },
    window: {
      location: {
        href: "https://example.org/agentic-ai-engineering/courses/agentic-ai-engineering/units/unit/lesson.html",
        origin: "https://example.org",
      },
      localStorage: {
        getItem(k) {
          assert.equal(k, key);
          return stored;
        },
        setItem(k, v) {
          assert.equal(k, key);
          if (blocked) throw Error("blocked");
          written = JSON.parse(v);
        },
      },
    },
    URL,
    Set,
    Date,
    JSON,
    Number,
    Boolean,
    String,
    Array,
    Object,
  };
  vm.runInNewContext(source, sandbox);
  return {
    button,
    challenge,
    root,
    label,
    value,
    status,
    written: () => written,
  };
}
let page = run();
assert.equal(page.button.hidden, false);
assert.equal(page.value.textContent, "0%");
page.button.listeners.click();
assert.equal(page.value.textContent, "50%");
assert.equal(page.button.attrs["aria-pressed"], "true");
assert.equal(
  Object.keys(page.written().courses["agentic-ai-engineering"].lessons).length,
  1,
);
page.button.listeners.click();
assert.equal(page.value.textContent, "0%");
for (const metadata of [
  { fcContentStatus: "planned" },
  { fcContentStatus: "draft" },
  { fcLessonId: "" },
  { fcLessonIds: "" },
  { fcLessonId: "unknown" },
]) {
  page = run(metadata);
  assert.equal(page.button.hidden, true);
  assert.equal(page.button.listeners.click, undefined);
  assert.equal(page.written(), null);
}
page = run({ fcLessonId: "", fcChallengeId: "unit.challenge" });
assert.equal(page.challenge.hidden, false);
page.challenge.listeners.click();
assert.equal(page.value.textContent, "50%");
page = run({}, "not json");
assert.equal(page.value.textContent, "0%");
for (const stored of [
  '{"schema_version":1,"courses":[]}',
  '{"schema_version":99,"courses":{}}',
  "null",
]) {
  assert.equal(run({}, stored).value.textContent, "0%");
}
const progress = {
  schema_version: 1,
  courses: {
    "agentic-ai-engineering": {
      curriculum_version: 1,
      rule_version: 1,
      lessons: { "unit.lesson": "date", retired: "date" },
      challenges: {},
    },
  },
};
assert.equal(run({}, JSON.stringify(progress)).value.textContent, "50%");
assert.equal(
  run({ fcCurriculumVersion: "2" }, JSON.stringify(progress)).value.textContent,
  "0%",
);
assert.equal(
  run({ fcCompletionRuleVersion: "2" }, JSON.stringify(progress)).value
    .textContent,
  "0%",
);
page = run({}, null, true);
page.button.listeners.click();
assert.match(page.status.textContent, /storage is unavailable/);
assert.equal(page.value.textContent, "50%");
