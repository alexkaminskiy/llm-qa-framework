# llm-qa-framework

An automated LLM evaluation framework built for validating RAG pipelines against Gold Standard datasets. Designed as a practical implementation of AI/LLM quality assurance patterns used in production environments.

## What this does

Runs a suite of DeepEval-based metrics against a local RAG pipeline on every push and nightly, publishing results to GitHub Pages. The framework validates three properties of LLM-generated answers:

| Test suite | Metric | What it catches |
|---|---|---|
| `test_rag_faithfulness` | FaithfulnessMetric ≥ 0.80 | Answer claims facts not in retrieved context |
| `test_answer_relevance` | AnswerRelevancyMetric ≥ 0.75 | Answer is tangential to the question asked |
| `test_rag_hallucination` | Direct string assertion | Model fabricates answers for out-of-corpus questions |

## Stack

| Component | Technology |
|---|---|
| Evaluation framework | [DeepEval](https://docs.confident-ai.com) 0.21.73 |
| RAG pipeline | LangChain 0.2 + FAISS |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, no API) |
| LLM + Judge | Groq `llama-3.3-70b-versatile` (free tier) |
| Test runner | pytest 8.3 |
| CI | GitHub Actions |
| Reports | pytest-html → GitHub Pages |

## Project structure

```
llm-qa-framework/
├── .github/
│   └── workflows/
│       └── eval-regression.yml   # CI pipeline + Pages deployment
├── evaluations/
│   ├── conftest.py               # RAGPipeline + GroqJudge fixtures
│   ├── test_rag_faithfulness.py  # Faithfulness metric tests
│   ├── test_answer_relevance.py  # Answer relevance metric tests
│   └── test_rag_hallucination.py # Out-of-context refusal tests
├── rag_pipeline/
│   ├── __init__.py
│   └── pipeline.py               # RAG system under test (FAISS + Groq)
├── datasets/
│   └── gold_standard.json        # Ground truth Q&A pairs
├── .env.example
└── requirements.txt
```

## Local setup

**Prerequisites:** Python 3.11+, Git

```bash
git clone https://github.com/alexkaminskiy/llm-qa-framework.git
cd llm-qa-framework

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your key:

```bash
cp .env.example .env
```

```env
GROQ_API_KEY=your_key_here
HF_HUB_DISABLE_SYMLINKS_WARNING=1   # Windows only
```

Get a free Groq API key at [console.groq.com](https://console.groq.com) — no credit card required.

## Running the tests

```bash
# Run full evaluation suite
pytest evaluations/ -v

# Run a specific metric only
pytest evaluations/test_rag_faithfulness.py -v

# Generate HTML report locally
pytest evaluations/ -v --html=reports/report.html --self-contained-html
```

On first run, `sentence-transformers` downloads the MiniLM model (~80MB) to `~/.cache/huggingface/`. Subsequent runs use the local cache.

## CI/CD

Every push to `main`, every pull request, and nightly at 06:00 UTC:

1. Installs dependencies
2. Runs the full evaluation suite against the Gold Standard dataset
3. Publishes the HTML report to GitHub Pages (even on failure)

**Live report:** [alexkaminskiy.github.io/llm-qa-framework/report.html](https://alexkaminskiy.github.io/llm-qa-framework/report.html)

Required secret: `GROQ_API_KEY` → Settings → Secrets → Actions

## Gold Standard dataset

`datasets/gold_standard.json` contains the ground truth Q&A pairs the RAG pipeline is evaluated against. Each entry has:

```json
{
  "id": "GS-001",
  "input": "What is the maximum payload of the F-35A?",
  "expected_output": "The F-35A has a maximum internal payload of 5,700 lbs...",
  "context_doc_ids": ["DOC-001"],
  "tags": ["factual", "defense"]
}
```

Tags control which tests apply to each sample. Samples tagged `out-of-context` are routed to the hallucination refusal test rather than semantic metric tests.

## Design decisions

**Why FAISS over ChromaDB/LanceDB?**
Both were evaluated. ChromaDB has native build dependency issues on Windows. LanceDB has an unstable API surface across minor versions with no consistent cross-platform wheel availability. FAISS is pure Python/numpy, installs cleanly on all platforms, and has a mature LangChain integration.

**Why Groq instead of OpenAI?**
Groq provides a free tier with no credit card requirement and ~500 req/min on `llama-3.3-70b-versatile`. For an evaluation framework used in CI, cost and rate limits matter. The same `DeepEvalBaseLLM` interface means swapping to OpenAI is a one-line config change.

**Why not use `HallucinationMetric` for in-context tests?**
`HallucinationMetric` evaluates each retrieved chunk independently. With `k=3` retrieval, only 1 of 3 chunks is relevant per question — the other 2 produce structural false positives regardless of answer quality. `FaithfulnessMetric` evaluates the combined context, which is the correct semantic for RAG validation.

## Extending the framework

**Add a new document to the corpus:** edit `DOCUMENTS` in `rag_pipeline/pipeline.py`, delete `faiss_store/`, re-run tests to rebuild the index.

**Add a new Gold Standard sample:** append an entry to `datasets/gold_standard.json` following the existing schema. No code changes needed.

**Add a new metric:** create a new test file in `evaluations/`, import from `deepeval.metrics`, use the `judge` and `rag_pipeline` fixtures from `conftest.py`.