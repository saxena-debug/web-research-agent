# Web Research Agent

A small AI agent that takes a research goal, searches the web, reads the actual content of each source, checks whether what it found is good enough, and writes a structured report. Built with Python, OpenAI GPT-4o, and the Tavily search API. The pipeline, prompts, and retry logic are written from scratch with no agent frameworks.


## What it does

You give it a goal like "best laptops under 1500 euros 2026" or "impact of LLMs on healthcare" and it handles the following on its own:

- Breaks the goal into a research plan
- Generates search queries from different angles
- Fetches full page content via Tavily
- Reads each source and pulls out only what is relevant to the goal
- Grades the quality of what it found. If the score is too low, it takes the evaluator's feedback and rewrites the queries before trying again
- Once quality passes, compiles everything into a structured report with an Executive Summary, Key Findings, and an Analysis section
- Saves the report as an HTML file and logs everything



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
```



## How to run it

Install dependencies:

```
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Run from the terminal:

```
python main.py "your research goal here"
```

To save the report to a specific folder:

```
python main.py "best laptops under 1500 euros 2026" --output ~/Desktop/reports
```

Or open the Streamlit UI:

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



## Logging

Three files are written to `logs/` on every run:

- `agent_runs.csv` has one row per run with the run ID, goal, status, start and end time, and total tokens used
- `task_events.csv` has one row per step with per-step timing, scores, retry reasons, and dropped source details
- `llm_traces.jsonl` has the full prompt and response for every LLM call, useful for debugging why a particular prompt returned something unexpected



## LLM wrapper

All LLM calls go through two functions in `llm.py`:

- `call_llm` for plain text responses
- `call_llm_json` for structured JSON responses

Every other file imports from here. If the provider or model changes, only `llm.py` needs to be updated.



## Configuration

All settings live in `config.yaml`. No values are hardcoded in the pipeline files.

```yaml
model: "gpt-4o"

agent:
  max_retries: 2              # how many times to retry if quality fails
  max_search_results: 3       # results per query from Tavily
  max_queries: 3              # queries generated per run (one per angle)
  max_summarize_sources: 5    # how many sources to fully read and summarize

depth:
  source_char_limit: 10000    # characters of raw page content read per source
  source_summary_sentences: 10
  exec_summary_sentences: 5
  analysis_paragraphs: 4

thresholds:
  quality: 0.6                # minimum score to pass grading

trust_filter:
  blocklist: [reddit.com, pinterest.com, quora.com, spam.com]
```

The depth settings directly affect report length and token cost. A higher `source_char_limit` gives the summarizer more material to work with and tends to produce richer summaries, but uses more tokens per source.


