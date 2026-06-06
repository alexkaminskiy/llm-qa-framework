---
title: LLM QA Framework
status: draft
created: 2026-06-05
updated: 2026-06-05
---

# LLM QA Framework: Automated Evaluation for RAG Pipelines

## Problem

Evaluating Large Language Model (LLM) applications is fundamentally harder than testing deterministic systems. RAG pipelines compound the challenge: they retrieve context dynamically, increasing surface area for hallucination, context drift, and retrieval failure. Without structured evaluation:

- **Output quality is invisible.** No systematic way to detect when an LLM starts producing less faithful, relevant, or coherent answers.
- **Regression goes undetected.** Prompt tweaks, model updates, or data changes can silently degrade performance.
- **Data integrity is assumed, not verified.** Corrupted or invalid source data flows undetected into retrieval and generation.
- **Security gaps stay hidden.** PII leaks and RBAC violations surface only in production or user reports.

This framework solves evaluation through practical implementation of industry QA patterns: DeepEval for LLM output quality, RAGAS for retrieval metrics, baseline tracking for regression detection, and data validation for corpus integrity.

## Solution Overview

A comprehensive, composable evaluation framework that validates LLM-based applications across **8 quality dimensions**:

| Layer | What it validates | Tools |
|---|---|---|
| **LLM output** | Faithfulness, relevance, refusal handling (hallucination prevention) | DeepEval metrics + Groq judge |
| **RAG pipeline** | Context precision, recall, answer correctness | RAGAS framework |
| **Prompt regression** | Score drift vs. committed baseline | DeepEval + custom baseline harness |
| **Data integrity** | Schema validity, business rule violations, domain constraints | Great Expectations + SQLite |
| **Vector store** | Index dimensions, retrieval accuracy, corpus consistency | FAISS + pytest |
| **Traceability** | Every test mapped to a system requirement | pytest markers + TRR generation |
| **RBAC enforcement** | Role-based access control across API endpoints | FastAPI + parameterized tests |
| **PII redaction** | No PII in API responses or LLM outputs | Regex patterns + RAG pipeline inspection |

The framework runs as a **pytest test suite** with CI integration, producing a **Test Readiness Review (TRR)** artifact that maps every test to a system requirement, suitable for regulated environments.

## Key Capabilities

### 1. LLM Output Quality (DeepEval)

Measure faithfulness (does the response stay grounded in context?), relevance (does it answer the question?), and hallucination prevention (does the LLM refuse out-of-scope queries?).

- **[ASSUMPTION]:** Using Groq's `llama-3.3-70b-versatile` as the evaluation judge (free tier, fast inference).
- Metrics are point-in-time; baseline tracking (see #3) detects degradation over time.

### 2. RAG Pipeline Metrics (RAGAS)

Evaluate retrieval quality independent of generation:

- **Context Precision:** What fraction of retrieved documents are relevant to the query?
- **Context Recall:** What fraction of ground-truth relevant documents did retrieval surface?
- **Answer Correctness:** Does the final answer match expected outputs?

Ground truth is **gold standard QA pairs** (user queries + expected answers) stored in `datasets/gold_standard.json`.

### 3. Baseline Regression Detection

Commit an evaluation baseline (`baseline.json`) after a known-good run. On subsequent runs:

- Compare current scores (faithfulness, relevance, context precision/recall) to baseline.
- Flag drift exceeding configurable thresholds (e.g., faithfulness drop > 5%).
- Prevent silent degradation from prompt tweaks or model updates.

### 4. Data Validation

Great Expectations checkpoints validate **source data** before it enters the pipeline:

- **Bill of Materials (BOM):** Schema compliance, required fields, numeric ranges.
- **Supplier Registry:** Risk scores, duplicate detection, reference integrity.
- **Custom SQL Rules:** Business logic (e.g., "no supplier with risk > 8 can be active").

Failures block pipeline execution; reports are generated for data owners.

### 5. Vector Store Integrity

FAISS index validation:

- Dimension correctness (index matches embedding model output size).
- Retrieval accuracy (documents returned match similarity thresholds).
- Corpus consistency (no orphaned embeddings, no duplicate vectors).

### 6. Traceability & Requirements Mapping

Every test is tagged with a system requirement ID (e.g., `@pytest.mark.requirement("SYS-REQ-001")`).

A **TRR generation script** (`scripts/generate_traceability.py`) produces:

- Markdown traceability matrix (test → requirement mapping).
- Coverage summary (% of requirements with test evidence).
- HTML/PDF report for sign-off.

### 7. RBAC Testing

Parameterized tests across all API endpoints and user roles (viewer, editor, admin, guest):

- **Positive cases:** Authorized roles access data.
- **Negative cases:** Unauthorized roles receive 403.
- **Cross-role isolation:** One role's data is invisible to another.

### 8. PII Redaction Audit

Scans API responses and LLM outputs for PII patterns:

- Email addresses, phone numbers, SSNs, API keys, credit card formats.
- Failures are reported; severity is flagged for remediation.

## Success Metrics

### Adoption Signals
- Baseline established for a RAG pipeline ✓
- Regression detected and acted upon ✓
- Data validation catches at least one real error ✓

### Quality Indicators
- Faithfulness score ≥ 0.75 on gold standard
- Context precision ≥ 0.70 (at least 70% of retrieved docs are relevant)
- Context recall ≥ 0.65 (retrieves 65%+ of relevant docs)
- Regression threshold not exceeded between runs

### Operational
- All 8 quality layers have at least one test ✓
- Traceability coverage ≥ 80% (80%+ of requirements have test evidence)
- RBAC matrix complete (all roles × endpoints tested)
- CI pipeline runs on every commit, reports TRR on merge to main

## Out of Scope

- **Real-time inference monitoring:** This framework is offline evaluation; production monitoring (latency, error rates, drift) is separate.
- **Automated remediation:** We detect and report; humans decide fixes.
- **LLM model training/fine-tuning:** This tests existing models; it does not train them.
- **Multi-modal evaluation:** Assumes text-in/text-out; images and video not supported.
- **Custom metric development:** Extends DeepEval and RAGAS; custom metrics require code.

## Technical Stack

| Component | Technology | Rationale |
|---|---|---|
| LLM evaluation | DeepEval 0.21.73 | Industry-standard, lightweight, supports custom metrics |
| RAG metrics | RAGAS 0.1.21 | Purpose-built for retrieval evaluation, modular |
| RAG pipeline (SUT) | LangChain 0.2 + FAISS | Simple, observable, reproducible |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Local, fast, no API costs |
| LLM + Judge | Groq llama-3.3-70b-versatile | Free tier, fast inference, reasonable quality |
| Data validation | Great Expectations 0.18.15 | Declarative, extensible, checkpoint-driven |
| SQL layer | SQLite + stdlib | Zero external dependencies, sufficient for evaluation |
| API under test | FastAPI 0.111 | Lightweight, async-friendly, RBAC-friendly |
| Auth | python-jose JWT | Standard tokens, role claims in payload |
| PDF generation | xhtml2pdf | Pure Python, no external tools |
| Test runner | pytest 8.3 | Mature, fixture-rich, plugin ecosystem |
| CI | GitHub Actions | Native to repo, free tier ample |
| Reports | pytest-html + GitHub Pages | Readable, static, no external hosting |

## Acceptance Criteria

- [ ] Framework runs end-to-end (test discovery → TRR generation) with no errors.
- [ ] All 8 quality dimensions have working test cases.
- [ ] Baseline captures and comparison detects a meaningful score change (manual test: tweak prompt, re-run, observe drift flag).
- [ ] Data validation catches schema or rule violation and blocks pipeline.
- [ ] RBAC matrix is complete and all tests pass.
- [ ] PII audit scans API responses and LLM outputs without false positives.
- [ ] TRR is generated with ≥80% requirement coverage.
- [ ] CI pipeline validates PRD-defined acceptance on each commit.

## Next Steps

1. **Validate PRD:** Walk through acceptance criteria, clarify assumptions.
2. **Create Architecture:** Decompose into epics (LLM metrics, data validation, RBAC, traceability, CI).
3. **Break into Stories:** Assign each epic to sprint-sized work.
4. **Sprint Planning:** Sequence stories (data validation early; CI last).
5. **Implement & Review:** Each story includes code + tests + TRR patch.

---

**Document History**

| Date | Author | Status | Notes |
|---|---|---|---|
| 2026-06-05 | Initial Draft | Draft | Fast Path discovery; awaiting review. |
