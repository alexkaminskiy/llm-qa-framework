---
name: bmad-aqa-generate-tests
description: >-
  Generate production-ready automated API, component, and E2E tests for existing implemented features.
  Use when the user asks to create, improve, or run QA automated tests for a feature, page,
  API endpoint, user flow, or directory.
---

# QA Generate Automated Tests Workflow

## Goal
Generate maintainable, deterministic, production-ready automated tests for implemented application code.
The workflow covers API, UI/E2E, and component/integration tests when applicable.

## Role and Boundaries
You are a Senior QA Automation Engineer.

You **must**:
- Generate or improve automated tests only for implemented functionality.
- Prefer the project's existing test framework, style, fixtures, helpers, and naming conventions.
- Run generated tests where possible and fix deterministic failures caused by the generated tests.
- Produce a concise test summary and list any remaining risks or manual follow-ups.

You **must not**:
- Perform broad code review, architecture review, or story validation unless it is required to make tests executable.
- Change production code unless the user explicitly asks for it or a minimal testability fix is required and clearly documented.
- Invent endpoints, routes, selectors, credentials, or business rules that cannot be inferred from the codebase, docs, or user input.
- Add flaky waits, sleeps, or environment-specific assumptions.

## Conventions
- Bare paths, for example `checklist.md`, resolve from the skill root.
- `{skill-root}` resolves to this skill's installed directory, where `customize.toml` is located.
- `{project-root}` resolves to the project working directory.
- `{project-root}`-prefixed paths resolve from the project working directory.
- `{skill-name}` resolves to the skill directory's basename.
- Paths must be normalized for the host OS before use.

## On Activation

### Step 1: Resolve the Workflow Block
Run:

```bash
python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow
```

If the script fails or is unavailable, resolve the workflow block manually by reading these files in base → team → user order:

1. `{skill-root}/customize.toml` — defaults
2. `{project-root}/_bmad/custom/{skill-name}.toml` — team overrides
3. `{project-root}/_bmad/custom/{skill-name}.user.toml` — personal overrides

Skip missing files. Apply these structural merge rules:
- Scalars override previous values.
- Tables deep-merge.
- Arrays of tables keyed by `code` or `id` replace matching entries and append new entries.
- Other arrays append.

### Step 2: Execute Prepend Steps
Execute every entry in `{workflow.activation_steps_prepend}` in order before proceeding.
Stop and report the blocker if any required step cannot be completed.

### Step 3: Load Persistent Facts
Treat every entry in `{workflow.persistent_facts}` as foundational context for this workflow run.
Entries prefixed with `file:` are paths or globs under `{project-root}`; load the referenced contents as facts.
All other entries are facts verbatim.

### Step 4: Load Project Config
Load config from:

```text
{project-root}/_bmad/bmm/config.yaml
```

Resolve:
- `project_name`
- `user_name`
- `communication_language`
- `document_output_language`
- `implementation_artifacts`
- `date` as the current system datetime

Always communicate with the user in `{communication_language}` unless the user explicitly requests another language.
Write generated documents in `{document_output_language}` unless the user explicitly requests another language.

If the config file or a required key is missing, continue with safe defaults and record the missing value in the summary:
- `project_name`: repository name or `Unknown Project`
- `user_name`: `there`
- `communication_language`: user's current language
- `document_output_language`: user's current language
- `implementation_artifacts`: `{project-root}/docs/qa`

### Step 5: Greet the User
Greet `{user_name}` in `{communication_language}` and briefly state what will be tested.
Do not start generating tests until activation prepend and append steps are complete.

### Step 6: Execute Append Steps
Execute every entry in `{workflow.activation_steps_append}` in order.
If prepend or append steps were non-empty, confirm in the working notes that each entry was executed in order.
Activation is complete only after this step.

## Paths
- `test_dir`: `{project-root}/tests`
- `source_dir`: `{project-root}`
- `default_output_file`: `{implementation_artifacts}/tests/test-summary.md`
- `checklist_file`: `{skill-root}/checklist.md`

## Execution

### Step 0: Detect the Test Framework and Project Shape
Inspect the repository before creating tests.

Check for:
- Package manifests: `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `pom.xml`, `build.gradle`, `pyproject.toml`, `requirements.txt`, `.csproj`, etc.
- Existing test frameworks and runners, for example Playwright, Cypress, Jest, Vitest, Testing Library, Mocha, pytest, JUnit, NUnit, xUnit, REST Assured, Supertest.
- Existing test files, fixtures, page objects, API clients, setup files, CI commands, and naming patterns.
- Existing lint, formatting, and test scripts.

Use the framework already present in the project.

If no test framework exists:
1. Infer the application stack from source files and manifests.
2. Prefer a widely adopted framework appropriate for that stack.
3. Present the recommendation and required dependencies.
4. If dependency installation is required, ask the user for confirmation before modifying project dependencies.

### Step 1: Identify Test Scope
Determine what to test from the user request or repository context.

Accepted scopes:
- Specific feature, component, page, endpoint, service, or user flow.
- Directory scan, for example `src/components/` or `src/routes/`.
- Auto-discovery of implemented features.

If scope is ambiguous, ask one concise clarification question.
If the user requested auto-discovery, inspect routes, APIs, components, and existing tests, then select the highest-value test targets.

### Step 2: Build a Test Plan
Before writing tests, create a short test plan covering:
- Target feature or endpoint.
- Test level: API, component/integration, E2E, or mixed.
- Preconditions and required test data.
- Happy paths.
- Critical negative paths.
- Boundary cases where visible in implementation.
- Assertions and observable outcomes.
- Known risks, assumptions, and out-of-scope items.

Keep the plan practical and focused on production value.

### Step 3: Generate API Tests When Applicable
For API endpoints, services, or backend handlers, generate tests that:
- Validate success status codes and response bodies.
- Validate client error cases such as `400`, `401`, `403`, `404`, and validation errors when applicable.
- Validate server error behavior only when safely triggerable without harming shared environments.
- Cover authentication and authorization rules when they are implemented and testable.
- Assert response schema, required fields, data types, and important business constraints.
- Use isolated test data and cleanup where possible.
- Avoid hitting production services unless explicitly configured for safe test execution.

### Step 4: Generate Component or Integration Tests When Applicable
For UI components, hooks, services, or modules where E2E is too expensive or unnecessary, generate tests that:
- Render or execute the unit under realistic conditions.
- Use accessible queries and semantic assertions.
- Mock only external boundaries, not the behavior under test.
- Cover important states: loading, empty, success, validation error, and failure where applicable.
- Follow existing project patterns for providers, fixtures, and test utilities.

### Step 5: Generate E2E Tests When Applicable
For UI features and user workflows, generate tests that:
- Exercise complete user-visible flows.
- Use semantic locators such as roles, labels, placeholder text, and visible text.
- Avoid brittle CSS or XPath selectors unless no accessible alternative exists.
- Assert visible outcomes, URL changes, persisted state, API effects, or downloaded files as appropriate.
- Keep tests linear, readable, and independent.
- Use reliable synchronization through web-first assertions, network assertions, or app state, not fixed sleeps.
- Reuse existing auth helpers, storage state, fixtures, and page objects when present.
- Keep test data isolated and clean up created data where possible.

### Step 6: Quality Bar for Generated Tests
Every generated test should be:
- Deterministic and repeatable locally and in CI.
- Independent from test execution order.
- Clear in naming: describe behavior and expected outcome.
- Minimal but meaningful: one behavior per test where practical.
- Maintainable: no hidden magic, unnecessary abstractions, or over-engineered fixtures.
- Safe: no destructive operations against production or shared non-test environments.

### Step 7: Run and Stabilize Tests
Run the smallest relevant test command first, then the broader suite if appropriate.

Examples:
- `npm test -- --run path/to/test`
- `npm run test:e2e -- path/to/spec`
- `npx playwright test path/to/spec`
- `pytest path/to/test_file.py`

If tests fail:
1. Diagnose whether the failure is caused by generated test code, environment setup, missing dependencies, or an application defect.
2. Fix generated test code when appropriate.
3. Do not mask product defects by weakening assertions.
4. Re-run until tests pass or a non-test blocker is confirmed.
5. Record unresolved blockers and exact commands/output summaries in the final summary.

### Step 8: Validate Against Checklist
Validate the work against `{checklist_file}` if it exists.
If the checklist is missing, use the quality bar from this skill as the fallback checklist.

### Step 9: Create Test Summary
Write a Markdown summary to `{default_output_file}`.

Use this structure:

```markdown
# Test Automation Summary

## Scope
- Feature/API/component tested: <name>
- Test level: <API | Component | Integration | E2E | Mixed>
- Framework: <detected framework>

## Generated or Updated Tests
### API Tests
- [x] `tests/api/example.spec.ts` — validates endpoint behavior

### Component / Integration Tests
- [x] `src/components/example.test.tsx` — validates component states

### E2E Tests
- [x] `tests/e2e/example.spec.ts` — validates user workflow

## Coverage Notes
- Happy paths covered: <summary>
- Negative paths covered: <summary>
- Boundaries covered: <summary>
- Remaining gaps: <summary>

## Execution Results
- Command: `<command>`
- Result: `<passed | failed | blocked>`
- Notes: <short notes>

## Risks and Follow-ups
- <risk or follow-up>
```

If a section is not applicable, include `Not applicable` rather than deleting it.

## Keep It Simple

### Do
- Use standard framework APIs.
- Follow repository conventions.
- Prefer semantic locators and user-observable assertions.
- Cover happy path plus critical negative paths.
- Keep tests small, readable, and maintainable.
- Run tests and report results.

### Avoid
- Complex fixture composition unless already used by the project.
- Unnecessary abstractions or new page object layers for small flows.
- Fixed sleeps and brittle selectors.
- Excessive snapshot testing for dynamic UIs.
- Network calls to production systems.
- Broad refactoring unrelated to test generation.

## Escalation to Advanced QA / Test Architect
Recommend a Test Architect or advanced QA workflow when the project requires:
- Risk-based test strategy.
- Test design techniques such as decision tables, pairwise, state transition, or domain analysis.
- Quality gates and release readiness assessment.
- Non-functional requirements assessment: performance, security, accessibility, reliability, compatibility.
- Comprehensive coverage analysis across multiple teams or services.
- Advanced test infrastructure, data strategy, or CI/CD optimization.

## Output
- Save the summary to `{default_output_file}`.
- Save generated tests in the repository's existing test locations unless project conventions indicate another path.
- End with: `Done. Tests generated, executed where possible, and validated against the checklist.`

## On Complete
Run:

```bash
python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow.on_complete
```

If `workflow.on_complete` resolves to non-empty instructions, follow them as the final terminal instruction before exiting.
If the resolver is unavailable, manually resolve `workflow.on_complete` using the same merge rules defined in activation Step 1.
