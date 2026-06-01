# Web Research Agent

A small AI agent that takes a research goal, searches the web, reads the actual content of each source, checks whether what it found is good enough, and writes a structured report. Built with Python, OpenAI GPT-4o, and the Tavily search API. The pipeline, prompts, and retry logic are written from scratch with no agent frameworks.


## What the agent does

You give it a research goal and it runs a full end-to-end pipeline without any human input in between. Here is exactly what happens:

- The goal is first checked by a dedicated safety model before anything else runs. If it is flagged, the run stops immediately and nothing is searched.
- GPT-4o breaks the goal into a task plan and generates multiple search queries covering different angles: a broad overview, a data and evidence angle, and a focused comparison angle.
- Tavily fetches full page content for each query. Low-quality domains like Reddit and Pinterest are blocked at the API level so they never appear in results.
- For each source, the agent reads the raw page content and extracts only what is relevant to the goal. Pages where nothing useful is found are dropped and logged.
- A quality grader scores the collected summaries from 0 to 1. If the score is below the threshold, it does not proceed to write the report.
- On a failed grade, the grader returns structured feedback: what was missing, what topics to cover, and specific query directions to try. The next search uses this feedback directly rather than repeating the same queries.
- Once the score passes, GPT-4o compiles a structured report with an Executive Summary, Key Findings, and an Analysis section, synthesizing across all sources rather than summarizing each one.
- The report is saved as an HTML file. Every run is fully logged including timings, scores, token usage, and all LLM calls.



## Project structure

```
agent.py          the main research loop
app.py            Streamlit UI
main.py           CLI entry point
tools.py          search and summarization functions
metrics.py        quality grading
prompts.py        all LLM prompts in one place
llm.py            central LLM wrapper (all calls go through here)
logger.py         structured logging to CSV and JSONL
report.py         HTML report generator
config.py         loads config.yaml and .env
config.yaml       all settings in one file
input_guardrail_check.py  safety check run before the pipeline starts
eval/performance_report.py  reads logs and exports a per-run performance CSV
tests/test_core.py        unit tests for config, grader, and prompts
tests/run_tests.py        runs tests and saves results to tests/results/
```



## How to run it

Follow these steps in order the first time you set up the project:

**Step 1. Clone the repo and enter the folder**
```
git clone https://github.com/saxena-debug/web-research-agent.git
cd web-research-agent
git checkout development
```

**Step 2. Create a virtual environment and activate it**
```
python -m venv .venv
source .venv/bin/activate
```

**Step 3. Install dependencies**
```
pip install -r requirements.txt
```

**Step 4. Set up your API keys**

Copy the example file and fill in your keys:
```
cp .env.example .env
```

Your `.env` should look like this:
```
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
GROQ_API_KEY=your_groq_api_key
```

- `OPENAI_API_KEY` is required for all LLM calls (GPT-4o)
- `TAVILY_API_KEY` is required for web search
- `GROQ_API_KEY` is optional but enables the input safety check

**Step 5. Optionally review config.yaml**

Open `config.yaml` to adjust query count, depth, retries, and quality threshold before your first run. The defaults work fine for most goals.

**Step 6. Run a research goal**

From the terminal:
```
python main.py "your research goal here"
```

To save the report to a specific folder:
```
python main.py "best laptops under 1500 euros 2026" --output ~/Desktop/reports
```

Or open the Streamlit UI for an interactive experience:
```
streamlit run app.py
```



## How the loop works

Everything runs inside `ResearchAgent.run()` in `agent.py`. Each step feeds into the next.

**Planning.** GPT-4o turns the goal into a short JSON task list. This is logged and shapes the run, but the pipeline is hardcoded for now and does not yet use the task list to drive execution. This is a known gap and is explained in the last section.

**Query expansion.** GPT-4o generates queries from three angles: a broad overview query, a data and evidence query, and one focused on a specific comparison or depth. The number of queries is set via `max_queries` in `config.yaml`.

If a previous attempt failed, the grader's feedback is injected here so the new queries actually address what was missing. For example if the grader returns `"missing_topics": "recent clinical trials"` and `"query_suggestions": "try PubMed or nature.com"`, the next expansion call sees exactly that text and targets those gaps specifically rather than repeating the same search.

**Web search.** Tavily searches each query and returns full page content along with images, favicons, and metadata. The domain blocklist (reddit, pinterest, quora, etc.) is applied at the API level so those results never come back.

**Source summarization.** For each source, the agent reads up to `source_char_limit` characters of raw page content and asks the model to extract only what is relevant to the goal. Sources where nothing relevant is found get dropped and logged.

This is what makes the reports meaningfully better than passing raw snippets. The compile step gets dense, focused context instead of raw HTML. For example, a source about laptop benchmarks might return a 12,000 character page. The agent reads the first 10,000 characters, extracts the specific models, prices, and performance numbers that match the goal, and passes only that summary forward.

**Quality grading.** A single GPT-4o call evaluates whether the summaries are good enough to write a report from. It returns a score from 0 to 1 along with structured feedback covering what issues exist, what topics are missing, and specific query directions to try next.

If the score is below the threshold, the feedback flows back into query expansion and the search runs again. The threshold defaults to 0.6 and can be adjusted from the Streamlit UI slider without editing any code.

**Compilation.** GPT-4o writes the final report from the source summaries, synthesizing across them rather than summarizing each one individually. The report structure, length, and depth are all configurable from `config.yaml`.



## How the score logic works

The quality grader runs after source summarization and before the report is written. It is a single GPT-4o call that reads all the source summaries alongside the original goal and returns a JSON object with four fields:

- `score` is a float from 0 to 1 representing how well the collected material answers the goal. 1 means excellent coverage, 0 means the sources are irrelevant or too thin.
- `issues` is a plain English description of what is wrong with the current results, for example "sources are paywalled and contain no usable content".
- `missing_topics` lists specific topics the goal requires but the sources did not cover, for example "pricing in euros" or "clinical trial results from 2024".
- `query_suggestions` gives concrete directions for the next search attempt, for example "search specifically on nature.com or pubmed" or "add 2025 to the query".

The threshold to pass is set in `config.yaml` under `thresholds.quality` and defaults to 0.6. It can also be adjusted from the Streamlit UI slider at runtime without changing any file.

If the score is at or above the threshold, the agent moves to compilation. If it is below, all four fields are injected into the next query expansion call so the new queries are shaped by exactly what was missing. This retry loop runs up to `max_retries` times before the agent gives up and returns whatever it has.

## Input safety

Before the pipeline starts, the research goal is passed to GPT-OSS-Safeguard-20B running via Groq. This is a dedicated safety model, completely separate from the GPT-4o model used for research.

If the goal is flagged as unsafe, the run stops immediately. Nothing is searched, no LLM calls are made for research, and the result is returned with a `blocked: true` flag and a violation category. The block is recorded in `agent_runs.csv` with the `blocked` and `violation` columns filled in.

If the Groq API key is not set, the safety check is skipped and the agent continues normally. This is a deliberate fail-open design so the agent stays usable in environments where the safety key is not configured.

The check lives entirely in `input_guardrail_check.py` and is called at the very top of `ResearchAgent.run()` before any timer or search logic starts.

## Logging

Three files are written to `logs/` on every run:

- `agent_runs.csv` has one row per run with the run ID, goal, status, start and end time, total tokens used, and two extra columns `blocked` and `violation` that are filled in when a run is stopped by the safety check
- `task_events.csv` has one row per step with per-step timing, scores, retry reasons, and dropped source details
- `llm_traces.jsonl` has the full prompt and response for every LLM call, useful for debugging why a particular prompt returned something unexpected



## LLM wrapper

All LLM calls go through two functions in `llm.py`:

- `call_llm` for plain text responses
- `call_llm_json` for structured JSON responses

Every other file imports from here. If the provider or model changes, only `llm.py` needs to be updated.



## Tests

Unit tests live in `tests/test_core.py` and cover three things: config loads correctly and all required keys are present, the quality grader passes or fails based on the threshold, and the prompts contain the goal text and correct settings.

To run the tests:

```
python tests/run_tests.py
```

Results are printed to the terminal and saved to `tests/results/test_results.csv` with a timestamp so you can track pass or fail over time.

## Evaluation

`performance_report.py` reads `logs/agent_runs.csv` and `logs/task_events.csv` and exports a per-run CSV to `eval/results/` covering wall time, token usage, quality score, retries, and per-step latency for every completed run.

```
python eval/performance_report.py
```

## Configuration

All settings live in `config.yaml`. No values are hardcoded in the pipeline files.

```yaml
model: "gpt-4o"                  # openai model to use for all llm calls

agent:
  max_retries: 2                 # how many times to retry if quality check fails
  max_search_results: 3          # results fetched per search query from tavily
  max_queries: 3                 # max number of queries in query expansion
  max_summarize_sources: 5       # max sources to fully read and summarize

depth:
  source_char_limit: 10000       # chars read per source page, higher means richer input but more tokens
  source_summary_sentences: 20   # sentences extracted per source summary
  exec_summary_sentences: 6      # sentences in the executive summary of the final report
  analysis_paragraphs: 6         # paragraphs in the analysis section of the final report

thresholds:
  quality: 0.7                   # minimum quality score to accept results (0 to 1)

trust_filter:
  blocklist:                     # domains excluded from search results
    - pinterest.com
    - spam.com

logging:
  log_dir: "logs"                # where agent run logs and traces are saved
  report_dir: "reports"          # where html reports are saved
```

The depth settings directly affect report length and token cost. A higher `source_char_limit` gives the summarizer more material to work with and tends to produce richer summaries, but uses more tokens per source.


