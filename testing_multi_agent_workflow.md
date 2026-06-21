# Testing a Multi-Agent Workflow with Latency & Redundant Tool-Call Issues

**Scenario:** A multi-agent workflow contains a **Planner Agent**, **Research Agent**, **Compliance Agent**, and **Writer Agent**. Occasionally the workflow produces correct results but takes excessive time and repeatedly invokes the same tools.

The symptom — *correct results, but slow with repeated identical tool calls* — points to an **efficiency / orchestration defect**, not a correctness one. Standard pass/fail assertions won't catch it. You need **process-level observability and trajectory testing** on top of output validation.

---

## 1. Make the Workflow Observable First

You can't test what you can't see. Instrument with tracing (OpenTelemetry / LangSmith / Langfuse / Arize Phoenix) to capture per-run:

- Full **trajectory**: agent → tool → args → result, in order
- **Tool-call ledger**: tool name + normalized arguments + timestamp + latency
- **Inter-agent handoffs** (Planner → Research → Compliance → Writer)
- Token usage, step count, wall-clock time, retries/loops

This turns a black box into an assertable event stream.

---

## 2. Define Metrics & SLOs That Target the Actual Defect

Beyond correctness, assert on **efficiency**:

| Metric | What It Catches |
|---|---|
| Redundant tool calls (count of duplicate tool + args) | The core symptom |
| Total tool calls per run | Over-invocation |
| Step / turn count per agent | Looping agents |
| End-to-end & per-agent latency (p50/p95/p99) | Excessive time |
| Cache-hit ratio | Whether memoization works |
| Token / cost per run | Economic regression |

Set SLOs, e.g. *"no identical tool call repeated > 1×"*, *"≤ N total tool calls"*, *"p95 latency < X s"*.

---

## 3. Trajectory / Process-Based Testing

Run a fixed, versioned eval set and assert on the *path*, not just the answer:

- **Duplicate-detection assertion**: hash each `(tool_name, normalized_args)`; fail if any hash repeats within a run. Normalize args (whitespace, casing, ordering) so semantically-identical calls are caught.
- **Loop detection**: flag cycles in the agent state graph (same agent/state visited repeatedly without progress).
- **Step-budget assertion**: hard cap on iterations; a run hitting the cap = failure signal.
- **Tool-call efficiency**: compare actual tool sequence against an expected/ideal trajectory (exact or fuzzy match).

---

## 4. Isolate *Which* Agent Causes It

Test each agent independently before integration:

- **Unit-level**: mock tools and downstream agents; feed the Planner a task and inspect whether its plan itself prescribes redundant steps. Often the root cause is a **bad plan** (Planner) or an agent **not reading prior context/scratchpad** and re-fetching.
- **Component swap (ablation)**: replace each agent with a stub returning known-good output; see when the redundancy disappears to localize the culprit.
- **Compliance/Research loop check**: a common pattern is Compliance rejecting → Writer/Research re-running the same retrieval. Verify rejection feedback is specific enough to avoid blind re-fetch.

---

## 5. Reproduce Reliably ("Occasionally" = Nondeterminism)

- Set `temperature=0` / fixed seeds where possible to stabilize.
- **Record-and-replay** tool responses (VCR-style) so the LLM decisions are the only variable.
- Run **N repetitions** per case (e.g. 20–50×) and measure **rate** of the slow/redundant behavior — since it's intermittent, single runs lie. Track flakiness as a metric.
- Build an adversarial set from real traces where the bug appeared.

---

## 6. LLM-as-Judge for Qualitative Efficiency

Use a judge model (with rubric) to score trajectories on *"was each tool call necessary?"* and *"did the agent reuse available information?"* — useful where deterministic rules miss semantic duplication. Validate the judge against human labels first.

---

## 7. Root-Cause Hypotheses to Validate

The tests should confirm/refute typical causes:

- **No memory of prior results** → agents re-call tools instead of reusing scratchpad/state → fix with shared memory + caching.
- **Weak termination criteria** → agents loop until max-iterations → fix stop conditions.
- **Planner over-decomposition** or replanning loops.
- **Missing tool-result cache / idempotency** → add a memoization layer and assert cache hits in tests.
- **Vague inter-agent feedback** causing rework cycles.

---

## 8. Put It in CI as Regression Gates

- Golden eval suite runs on every prompt/model/orchestration change.
- **Fail the build** on regressions in: redundant-call count, step count, p95 latency, cost — not just accuracy.
- Track these metrics over time on a dashboard to catch slow drift.

---

## Summary

Treat it as a **trajectory + efficiency testing problem**:

1. Instrument for full observability.
2. Assert on tool-call ledgers / step budgets / latency SLOs (not just final output).
3. Isolate the offending agent via mocking/ablation.
4. Run repeated seeded executions to quantify the intermittent behavior.
5. Gate it all in CI.
