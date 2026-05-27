# llm-qa-framework

An automated LLM evaluation framework for validating RAG pipelines against Gold Standard datasets, with data quality validation, prompt regression detection, and formal V&V traceability. Built as a practical implementation of AI/LLM quality assurance patterns used in defense and regulated environments.

## What this does

| Layer | What it validates | Tools |
|---|---|---|
| LLM output quality | Faithfulness, relevance, hallucination prevention | DeepEval |
| RAG pipeline metrics | Context precision, recall, answer correctness | RAGAS |
| Prompt regression | Score drift vs committed baseline | DeepEval + custom harness |
| Data integrity | BOM schema, supplier validity, SQL business rules | Great Expectations + SQLite |
| Vector store | Index dimensions, retrieval accuracy, corpus integrity | FAISS + pytest |
| Traceability | Every test mapped to a system requirement | pytest markers + TRR |

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
├── tests/                           # Data + infrastructure tests
│   ├── test_data_validation.py      # GE checkpoints + SQL validation
│   └── test_vector_store.py         # FAISS index integrity + retrieval
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
│   └── system_requirements.json     # System requirements registry (SYS-REQ-001..013)
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

Copy `.env.example` to `.env` and fill in your key:

```env
GROQ_API_KEY=your_key_here
HF_HUB_DISABLE_SYMLINKS_WARNING=1   # Windows only
```

Get a free Groq API key at https://console.groq.com — no credit card required.

## Running the tests

```bash
# Full suite (LLM eval + data validation + vector store)
pytest -v

# LLM evaluation only (~2 min, requires Groq API key)
pytest evaluations/ -v

# Data validation + vector store only (~30 sec, no API calls)
pytest tests/ -v

# Single metric
pytest evaluations/test_rag_faithfulness.py -v

# With HTML report
pytest -v --html=reports/report.html --self-contained-html
```

## Phase 2 — Prompt Regression Harness

Detects silent quality drift by comparing current scores against a committed baseline.

### Capture a new baseline

```bash
python scripts/capture_baseline.py
```

Writes scores to `baselines/baseline.json` tagged with model version, prompt version, and commit SHA. Commit the result.

### How regression detection works

```
baseline.json  <-- established reference (committed to repo)
      |
      |  delta = baseline_score - current_score
      |  if delta > 0.05 -> REGRESSION DETECTED
      v
test_prompt_regression.py  <-- runs on every push
```

Two levels: per-sample (catches regressions on specific inputs) and aggregate (catches distributed drift).

### Update baseline via CI

Actions -> LLM Eval Regression -> Run workflow -> update_baseline=true

Never update the baseline to silence a regression. Fix the root cause first.

## Phase 3 — Data Validation

Three-layer validation for the defense supply chain dataset.

**Layer 1: CSV / pandas** — schema, format, completeness, business rules via Great Expectations checkpoints.

**Layer 2: SQL** — referential integrity, aggregate business rules, and compliance checks:
- BOM supplier IDs must exist in the supplier register
- No category sole-sourced from a high-risk supplier
- SECRET parts must not come from non-US suppliers (ITAR)

**Layer 3: Vector store** — FAISS index dimensionality, vector count, and retrieval accuracy for known queries.

```bash
pytest tests/ -v
```

## Phase 4 — V&V Traceability

Every test maps to a system requirement. The traceability matrix and TRR are generated automatically after each run.

### 13 system requirements across 4 categories

- AI quality: SYS-REQ-001 to 004
- Data integrity: SYS-REQ-005 to 007, 011
- Compliance: SYS-REQ-008, 012, 013
- System integrity: SYS-REQ-009 to 010

### Generate TRR and traceability matrix

```bash
# Full run (fresh outcomes)
pytest -v --junit-xml=reports/results.xml
python scripts/generate_traceability.py

# Without re-running LLM tests
pytest tests/ -v --junit-xml=reports/results.xml
python scripts/patch_traceability.py
python scripts/generate_traceability.py
```

Outputs:
- `reports/traceability_matrix.csv` — machine-readable requirement coverage
- `docs/TRR.md` — Test Readiness Review document
- `docs/TRR.pdf` — PDF for Stage Gate submission

## CI/CD

Runs on every push to main, every pull request, and nightly at 06:00 UTC.

Pipeline steps:
1. Run full evaluation suite
2. Compare results against baseline (regression check)
3. Generate traceability matrix and TRR
4. Publish HTML report to GitHub Pages

**Live report:** https://alexkaminskiy.github.io/llm-qa-framework

Required secret: GROQ_API_KEY -> Settings -> Secrets -> Actions

| workflow_dispatch input | Effect |
|---|---|
| update_baseline=true | Captures fresh baseline, commits baseline.json |

## Gold Standard dataset

`datasets/gold_standard.json` — ground truth Q&A pairs. Tags control metric routing:

| Tag | Applied metrics |
|---|---|
| factual, defense | FaithfulnessMetric + AnswerRelevancyMetric |
| out-of-context | Refusal test only |
| adversarial | Hallucination trap |

## Design decisions

**Why FAISS over ChromaDB/LanceDB?**
Both were evaluated. ChromaDB has native build issues on Windows. LanceDB has an unstable API surface across minor versions — `lancedb.rerankers` missing on Linux 0.3.x, `list_tables()` API split across versions. FAISS is pure Python/numpy, installs cleanly everywhere.

**Why Groq instead of OpenAI?**
Free tier, no credit card, ~500 req/min. The `DeepEvalBaseLLM` interface means swapping judges is a one-line config change.

**Why not HallucinationMetric for in-context tests?**
It evaluates each chunk independently. With k=3, 2 of 3 chunks are irrelevant to any question — producing structural false positives. FaithfulnessMetric evaluates the combined context, which is correct for RAG.

**Why sqlite3 instead of SQLAlchemy for pandas integration?**
SQLAlchemy 2.x removed DBAPI2 cursor compatibility from connection objects, which pd.read_sql() requires. sqlite3 is stdlib and natively DBAPI2-compliant.

**Why xhtml2pdf instead of WeasyPrint?**
WeasyPrint requires GTK native libraries unavailable on Windows without a ~500MB system install. xhtml2pdf is pure Python with no native dependencies.

**Why commit baseline.json to the repo?**
A baseline update in a PR is a visible signal that quality characteristics changed. Git history shows quality evolution. Rolling back is a git revert.

## Extending the framework

**Add a document to the corpus:** edit `DOCUMENTS` in `rag_pipeline/pipeline.py`, delete `faiss_store/`, re-run tests.

**Add a Gold Standard sample:** append to `datasets/gold_standard.json` — parametrize picks it up automatically.

**Add a system requirement:** add to `requirements/system_requirements.json`, add `@pytest.mark.requirement("SYS-REQ-NEW")` to relevant tests, regenerate TRR.

**Add a metric:** create a test file in `evaluations/`, use `judge` and `rag_pipeline` fixtures from `evaluations/conftest.py`.

**Add a data validation rule:** add an expectation to `data_validation/suites.py` or a new SQL test in `tests/test_data_validation.py`.