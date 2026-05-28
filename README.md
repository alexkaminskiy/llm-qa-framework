# llm-qa-framework

An automated LLM evaluation framework for validating RAG pipelines against Gold Standard datasets, with data quality validation, prompt regression detection, formal V&V traceability, and security API testing. Built as a practical implementation of AI/LLM quality assurance patterns used in defense and regulated environments.

## What this does

| Layer | What it validates | Tools |
|---|---|---|
| LLM output quality | Faithfulness, relevance, hallucination prevention | DeepEval |
| RAG pipeline metrics | Context precision, recall, answer correctness | RAGAS |
| Prompt regression | Score drift vs committed baseline | DeepEval + custom harness |
| Data integrity | BOM schema, supplier validity, SQL business rules | Great Expectations + SQLite |
| Vector store | Index dimensions, retrieval accuracy, corpus integrity | FAISS + pytest |
| Traceability | Every test mapped to a system requirement | pytest markers + TRR |
| RBAC enforcement | Role-based access control across all API endpoints | FastAPI + pytest |
| PII redaction | No PII in API responses or LLM outputs | Regex patterns + RAG pipeline |

## Project structure

```
llm-qa-framework/
├── .github/
│   └── workflows/
│       └── eval-regression.yml      # CI pipeline + Pages + TRR generation
│
├── evaluations/                     # LLM evaluation tests
│   ├── conftest.py                  # RAGPipeline, GroqJudge, RAGAS fixtures
│   ├── judge.py                     # Shared GroqJudge class
│   ├── test_rag_faithfulness.py     # DeepEval FaithfulnessMetric [SYS-REQ-001]
│   ├── test_answer_relevance.py     # DeepEval AnswerRelevancyMetric [SYS-REQ-002]
│   ├── test_rag_hallucination.py    # Out-of-context refusal [SYS-REQ-003]
│   ├── test_prompt_regression.py    # Baseline delta tests [SYS-REQ-004]
│   └── test_ragas_metrics.py        # RAGAS context precision + recall
│
├── tests/                           # Data, infrastructure, and security tests
│   ├── test_data_validation.py      # GE checkpoints + SQL validation
│   ├── test_vector_store.py         # FAISS index integrity + retrieval
│   ├── test_rbac.py                 # Parameterized RBAC matrix [SYS-REQ-014]
│   └── test_pii_redaction.py        # PII detection: API + LLM [SYS-REQ-015/016]
│
├── api/                             # Mock FastAPI application (system under test)
│   ├── __init__.py
│   ├── app.py                       # Endpoints with RBAC enforcement
│   └── auth.py                      # JWT tokens + role permissions
│
├── rag_pipeline/
│   ├── __init__.py
│   └── pipeline.py                  # RAG system under test (FAISS + Groq)
│
├── data_validation/
│   ├── __init__.py
│   ├── setup_db.py                  # Loads CSVs into SQLite
│   └── suites.py                    # Great Expectations suite definitions
│
├── data/
│   ├── bom.csv                      # Sample Bill of Materials
│   └── suppliers.csv                # Sample supplier risk register
│
├── datasets/
│   └── gold_standard.json           # Ground truth Q&A pairs
│
├── baselines/
│   └── baseline.json                # Committed evaluation baseline
│
├── requirements/
│   └── system_requirements.json     # Requirements registry (SYS-REQ-001..016)
│
├── docs/
│   ├── TRR.md                       # Test Readiness Review (generated)
│   └── TRR.pdf                      # TRR in PDF format (generated)
│
├── scripts/
│   ├── capture_baseline.py          # Updates baseline.json from fresh eval run
│   ├── generate_traceability.py     # Generates TRR + traceability matrix
│   └── patch_traceability.py        # Rebuilds traceability without re-running LLM tests
│
├── conftest.py                      # Root: captures requirement markers per test
├── pytest.ini                       # Test discovery, asyncio mode, marker registration
├── requirements.txt
└── .env.example
```

## Stack

| Component | Technology |
|---|---|
| LLM evaluation | DeepEval 0.21.73 |
| RAG metrics | RAGAS 0.1.21 |
| RAG pipeline | LangChain 0.2 + FAISS |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 (local) |
| LLM + Judge | Groq llama-3.3-70b-versatile (free tier) |
| Data validation | Great Expectations 0.18.15 |
| SQL layer | SQLite + sqlite3 (stdlib) |
| API under test | FastAPI 0.111 + python-jose JWT |
| PDF generation | xhtml2pdf (pure Python) |
| Test runner | pytest 8.3 |
| CI | GitHub Actions |
| Reports | pytest-html + GitHub Pages |

## Local setup

**Prerequisites:** Python 3.11+, Git, pandoc

```bash
git clone https://github.com/alexkaminskiy/llm-qa-framework.git
cd llm-qa-framework

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copy `.env.example` to `.env`:

```env
GROQ_API_KEY=your_key_here
HF_HUB_DISABLE_SYMLINKS_WARNING=1   # Windows only
```

Get a free Groq API key at https://console.groq.com — no credit card required.

## Running the tests

```bash
# Full suite
pytest -v

# By phase
pytest evaluations/ -v                          # Phase 1+2: LLM evaluation
pytest tests/test_data_validation.py -v         # Phase 3: data validation
pytest tests/test_vector_store.py -v            # Phase 3: vector store
pytest tests/test_rbac.py -v                    # Phase 5: RBAC (fast, no API calls)
pytest tests/test_pii_redaction.py -v           # Phase 5: PII redaction

# With HTML report
pytest -v --html=reports/report.html --self-contained-html
```

## Phase 2 — Prompt Regression Harness

Detects silent quality drift by comparing current scores against a committed baseline.

```bash
# Capture a new baseline
python scripts/capture_baseline.py
```

Two levels of detection: per-sample (catches regressions on specific inputs) and aggregate (catches distributed drift).

Update baseline via CI: Actions → LLM Eval Regression → Run workflow → `update_baseline=true`

> Never update the baseline to silence a regression. Fix the root cause first.

## Phase 3 — Data Validation

**Layer 1: CSV / pandas** — schema, format, completeness, business rules via Great Expectations.

**Layer 2: SQL** — referential integrity and compliance checks via SQLite:
- BOM supplier IDs must exist in the supplier register
- No category sole-sourced from a high-risk supplier
- SECRET parts must not come from non-US suppliers (ITAR)

**Layer 3: Vector store** — FAISS index dimensionality, vector count, retrieval accuracy.

## Phase 4 — V&V Traceability

16 system requirements across 5 categories. Every test maps to at least one requirement via `@pytest.mark.requirement("SYS-REQ-XXX")`.

```bash
# Generate TRR — fast path (uses last XML, no LLM re-run)
pytest tests/ -v --junit-xml=reports/results.xml
python scripts/patch_traceability.py
python scripts/generate_traceability.py
```

Outputs: `reports/traceability_matrix.csv`, `docs/TRR.md`, `docs/TRR.pdf`

## Phase 5 — Security API Testing

### RBAC enforcement

The mock FastAPI application implements four roles with distinct permission sets:

| Role | Permissions |
|---|---|
| `guest` | None — 401 on all protected endpoints |
| `analyst` | BOM read, supplier list read |
| `engineer` | + risk scores, classified specs |
| `admin` | + contact PII, user management |

25 parameterized test cases cover every (role, endpoint) combination. Any 200 where 403 is expected is a privilege escalation. Any 403 where 200 is expected is a legitimate user being locked out.

```bash
pytest tests/test_rbac.py -v   # runs in-process, no network, ~3 seconds
```

### PII redaction

Two surfaces tested:

**API layer** — endpoints gated behind `contact:read` and `users:read` permissions must return 403 to lower-privilege roles, and the 403 error body must contain no PII (a common leakage vector).

**LLM layer** — the RAG pipeline is queried with six PII-fishing prompts. The corpus contains no personal data, so any PII in the output is hallucinated. Both the absence of PII patterns and the presence of a refusal phrase are asserted.

```bash
pytest tests/test_pii_redaction.py::TestAPIPIIRedaction -v   # fast
pytest tests/test_pii_redaction.py::TestLLMPIIPrevention -v  # uses Groq
```

### PII patterns detected

| Type | Pattern |
|---|---|
| Email | `name@domain.tld` |
| SSN | `NNN-NN-NNNN` |
| US phone | `(NNN) NNN-NNNN` or `NNN-NNN-NNNN` |
| International phone | `+NN NNN NNNN` |
| Credit card | `NNNN NNNN NNNN NNNN` |

## CI/CD

Runs on every push to `develop`, every PR, and nightly at 06:00 UTC.

1. Runs full evaluation suite (LLM + data + security)
2. Compares results against baseline (regression check)
3. Generates traceability matrix and TRR
4. Publishes HTML report to GitHub Pages

**Live report:** https://alexkaminskiy.github.io/llm-qa-framework

Required secret: `GROQ_API_KEY` → Settings → Secrets → Actions

| workflow_dispatch input | Effect |
|---|---|
| `update_baseline=true` | Captures fresh baseline, commits baseline.json |

## System requirements coverage

| ID | Title | Category | Covered by |
|---|---|---|---|
| SYS-REQ-001 | RAG Output Faithfulness | AI Quality | test_rag_faithfulness |
| SYS-REQ-002 | RAG Answer Relevance | AI Quality | test_answer_relevance |
| SYS-REQ-003 | Out-of-Context Refusal | AI Safety | test_rag_hallucination |
| SYS-REQ-004 | Prompt Regression Prevention | AI Quality | test_prompt_regression |
| SYS-REQ-005 | BOM Schema Compliance | Data Integrity | test_data_validation |
| SYS-REQ-006 | Supplier Data Validity | Data Integrity | test_data_validation |
| SYS-REQ-007 | Referential Integrity | Data Integrity | test_data_validation |
| SYS-REQ-008 | ITAR Compliance | Compliance | test_data_validation |
| SYS-REQ-009 | Vector Index Integrity | System Integrity | test_vector_store |
| SYS-REQ-010 | Retrieval Accuracy | System Integrity | test_vector_store |
| SYS-REQ-011 | BOM Value Plausibility | Data Integrity | test_data_validation |
| SYS-REQ-012 | Supplier Audit Timeliness | Compliance | test_data_validation |
| SYS-REQ-013 | Supply Chain Diversification | Compliance | test_data_validation |
| SYS-REQ-014 | RBAC Enforcement | Security | test_rbac |
| SYS-REQ-015 | API PII Redaction | Security | test_pii_redaction |
| SYS-REQ-016 | LLM PII Prevention | AI Safety | test_pii_redaction |

## Design decisions

**Why FAISS over ChromaDB/LanceDB?**
Both were evaluated. ChromaDB has native build issues on Windows. LanceDB has an unstable API across minor versions. FAISS is pure Python/numpy, installs cleanly everywhere.

**Why Groq instead of OpenAI?**
Free tier, no credit card. The `DeepEvalBaseLLM` interface means swapping judges is a one-line config change.

**Why not HallucinationMetric for in-context tests?**
It evaluates each chunk independently. With k=3, structural false positives occur. FaithfulnessMetric evaluates combined context — correct for RAG.

**Why sqlite3 instead of SQLAlchemy for pandas?**
SQLAlchemy 2.x removed DBAPI2 cursor compatibility. sqlite3 is stdlib and natively DBAPI2-compliant.

**Why xhtml2pdf instead of WeasyPrint?**
WeasyPrint requires GTK native libraries unavailable on Windows without a ~500MB install. xhtml2pdf is pure Python.

**Why a mock FastAPI for RBAC testing?**
Testing RBAC against a real SAP/Ariba system requires credentials, network access, and test data isolation. A mock API is self-contained, deterministic, fast, and demonstrates the same test patterns that apply to any JWT-protected REST API.

**Why assert on 403 error bodies for PII?**
Error messages are a common overlooked leakage vector. A well-designed RBAC system returns a generic 403 with no data about the protected resource. Testing the error body explicitly catches cases where the API echoes back request parameters or resource metadata in the error response.

## Extending the framework

**Add an API endpoint:** add it to `api/app.py`, add the corresponding rows to `RBAC_MATRIX` in `test_rbac.py`.

**Add a PII pattern:** add the regex to `_PII_PATTERNS` in `test_pii_redaction.py` — it will be applied to all existing PII tests automatically.

**Add a document to the corpus:** edit `DOCUMENTS` in `rag_pipeline/pipeline.py`, delete `faiss_store/`, re-run tests.

**Add a Gold Standard sample:** append to `datasets/gold_standard.json` — parametrize picks it up automatically.

**Add a system requirement:** add to `requirements/system_requirements.json`, add `@pytest.mark.requirement("SYS-REQ-NEW")` to relevant tests, regenerate TRR.