import re
import streamlit as st
import threading
import queue
from agent import ResearchAgent
from report import export_html

st.set_page_config(page_title="Web Research Agent", layout="centered")
st.title("Web Research Agent")
st.caption('Ask anything — "best laptops under €1500", "impact of LLMs on healthcare 2026", "top EVs in Europe". The agent searches the web, reads full sources, evaluates quality, and compiles a structured report with analysis.')

goal = st.text_input("Research goal", placeholder="e.g. best laptops under 1500 euros 2026")

st.caption(
    "Quality threshold — minimum score the agent must reach before writing the report. "
    "Lower is more lenient, higher forces the agent to retry until it finds better sources. "
    "0.6 works for most goals; raise to 0.8+ for research where accuracy matters more."
)
quality_threshold = st.slider(
    "Quality threshold",
    min_value=0.1,
    max_value=1.0,
    value=0.6,
    step=0.05,
)

run_btn = st.button("Run", type="primary")

if run_btn and goal.strip():
    log_queue = queue.Queue()

    def run_agent():
        agent = ResearchAgent()
        result = agent.run(goal, quality_threshold=quality_threshold, callback=lambda e: log_queue.put(e))
        log_queue.put({"status": "finished", "result": result})

    thread = threading.Thread(target=run_agent)
    thread.start()

    st.subheader("Progress")
    status_area = st.empty()
    log_lines = []

    while True:
        try:
            event = log_queue.get(timeout=300)
        except queue.Empty:
            st.error("Agent timed out.")
            break

        if event["status"] == "finished":
            result = event["result"]

            # quality never passed — show message, dont generate report
            if result.get("low_quality"):
                st.warning(result.get("report", "Quality threshold not met."))
                break

            path = export_html(result)

            st.success("Done in " + str(result["total_time"]) + "s")

            col1, col2, col3 = st.columns(3)
            col1.metric("Quality Score", "%.2f / 1.0" % result["quality_score"])
            col2.metric("Threshold", "%.2f" % quality_threshold)
            col3.metric("Tokens Used", "{:,}".format(result["total_tokens"]))

            with st.expander("What is the Quality Score?"):
                st.markdown('''
**Quality Score** (0 – 1) is an automated evaluation of whether the search results were
good enough to write a reliable report from. It is computed by asking the LLM to assess
the collected source summaries against three criteria:

- **Relevance** — are at least half the sources directly on-topic for the goal?
- **Evidence quality** — do they contain real facts, figures, and conclusions (not just vague overviews)?
- **Recency** — are sources recent enough to be useful (within ~2 years)?

If the score is below the threshold you set, the agent rewrites its search queries using
the evaluator's specific feedback and retries. The score shown is from the final attempt.
''')

            breakdown = result.get("token_breakdown", {})
            if breakdown:
                with st.expander("Token breakdown"):
                    st.markdown("Tokens are consumed at each LLM step. Here's where they went:")
                    labels = {
                        "plan":              "Planning (structuring the research tasks)",
                        "query_expansion":   "Query expansion (generating search queries, incl. retries)",
                        "summarize_sources": "Summarizing sources (reading each page, ~6 LLM calls)",
                        "quality_check":     "Quality check (grading relevance & evidence, incl. retries)",
                        "compile":           "Compiling report (writing the final report)",
                    }
                    total = result["total_tokens"]
                    for key, label in labels.items():
                        count = breakdown.get(key, 0)
                        pct = (count / total * 100) if total else 0
                        st.markdown("**" + label + "**")
                        st.progress(pct / 100, text="{:,} tokens ({:.0f}%)".format(count, pct))

            st.subheader("Report")
            with open(path) as f:
                html_content = f.read()
            embed_html = re.sub(
                r'<div class="sources-section">.*?(?=</body>)',
                '',
                html_content,
                flags=re.DOTALL,
            )
            st.components.v1.html(embed_html, height=700, scrolling=True)

            st.caption("Run ID: " + result["run_id"] + " | Report saved to " + path)
            break

        icon = "✓" if event["status"] == "done" else ("!" if event["status"] == "retry" else "›")
        log_lines.append(icon + "  " + event["msg"])
        status_area.code("\n".join(log_lines))

elif run_btn and not goal.strip():
    st.warning("Please enter a research goal.")
