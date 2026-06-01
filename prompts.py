import config


def plan_prompt(goal):
    return (
        "Break this research goal into a clear step by step plan.\n"
        "Return a JSON list where each item has: id, task, tool.\n"
        "Tool must be one of: search, compile.\n"
        "Keep it to 4-6 tasks maximum.\n\n"
        "Goal: " + goal + "\n\n"
        "Return only valid JSON, no explanation."
    )


def expand_queries_prompt(goal, feedback=None):

    n = str(config.MAX_QUERIES)

    '''because my previous attempt failed, I inject the graders feedback so the queries
    actually change: without this the retry just runs the same search again'''
    feedback_section = ""
    if feedback:
        missing   = feedback.get("missing_topics", "")
        issues    = feedback.get("issues", "")
        suggested = feedback.get("query_suggestions", "")

        feedback_section = "\n\nThe previous search attempt was not good enough. Here is what went wrong:\n"

        if issues:
            feedback_section += "Issues: " + issues + "\n"
        if missing:
            feedback_section += "Topics not covered: " + missing + "\n"
        if suggested:
            feedback_section += "Suggested directions to try: " + suggested + "\n"

        feedback_section += "\nYour new queries must directly address these issues. Do not repeat the previous approach.\n"

    return (
        "You are a research assistant generating search queries for a web research agent.\n"
        "Your queries should find authoritative, detailed, and current sources — "
        "reports, studies, expert analysis, industry data, and in-depth articles.\n\n"
        "Generate " + n + " search queries for the following research goal.\n\n"
        "Each query must target a different angle:\n"
        "Query 1: broad overview — current state, key players, main findings\n"
        "Query 2: data and evidence — statistics, studies, benchmarks, research papers\n"
        "Query 3: specific depth — expert opinion, comparisons, or a focused sub-topic\n\n"
        "Guidelines:\n"
        "Preserve all constraints from the goal such as price, currency, category, location, and year.\n"
        "Prefer queries that would surface expert sources over generic listicles.\n"
        "Include the current year (2026) in at least one query to get up-to-date results.\n"
        "Keep each query concise, under 12 words."
        + feedback_section + "\n\n"
        "Goal: " + goal + "\n\n"
        "Return a JSON list of " + n + " strings only. Return only valid JSON, no explanation."
    )


def summarize_source_prompt(goal, title, content):
    sentences = str(config.SOURCE_SUMMARY_SENTENCES)
    return (
        "You are a research assistant extracting relevant information from a web page.\n\n"
        "Research goal: " + goal + "\n\n"
        "Page title: " + title + "\n"
        "Page content:\n"
        + content + "\n\n"
        "Extract and summarize only the information from this page that is directly useful for the research goal.\n"
        "Be specific and include facts, figures, dates, names, comparisons, and conclusions.\n"
        "Ignore navigation menus, ads, and anything unrelated to the goal.\n"
        "Write up to " + sentences + " sentences and be as detailed as the content allows.\n"
        "If the page has no relevant information at all, respond with exactly: Not relevant.\n"
    )


def grade_results_prompt(goal, results, threshold=None):

    cutoff = threshold if threshold is not None else config.QUALITY_THRESHOLD
    return (
        "You are evaluating whether search results are good enough to write a research report from.\n\n"
        "Goal: " + goal + "\n\n"
        "Results:\n"
        + results + "\n\n"
        "Grading guidelines:\n"
        "Focus on whether the results contain real, useful information to answer the goal.\n"
        "Minor currency differences such as USD vs EUR are acceptable and should not cause a fail.\n"
        "Only penalise heavily if results are completely off-topic, older than 2 years, or contain no useful information.\n"
        "If at least half the results are relevant and informative, lean towards passing.\n\n"
        "Return JSON only:\n"
        "{\n"
        '  "binary_score": "yes or no",\n'
        '  "score": 0.0,\n'
        '  "issues": "what is wrong with the current results",\n'
        '  "missing_topics": "specific topics or angles that are missing",\n'
        '  "query_suggestions": "concrete alternative query directions to try next"\n'
        "}\n\n"
        '"score" is 0 to 1. Set "binary_score" to yes if score >= ' + str(round(cutoff, 2)) + '.'
    )


def compile_prompt(goal, summaries):
    exec_sentences = str(config.EXEC_SUMMARY_SENTENCES)
    analysis_paras = str(config.ANALYSIS_PARAGRAPHS)
    return (
        "You are a research analyst writing a detailed report from multiple web sources.\n"
        "Your job is to synthesize the sources into a coherent, thorough report — not just summarize each one.\n\n"
        "Research goal: " + goal + "\n\n"
        "Source summaries:\n"
        + summaries + "\n\n"
        "Write a detailed research report with this structure:\n"
        "1. Executive Summary: " + exec_sentences + " sentences covering the overall picture\n"
        "2. Key Findings: detailed points covering all important facts, figures, trends, and comparisons. Note where sources agree or contradict each other.\n"
        "3. Analysis: " + analysis_paras + " paragraphs drawing conclusions, identifying patterns, and highlighting what matters most\n\n"
        "Important:\n"
        "This is a research document so be thorough and include all relevant detail from the sources.\n"
        "Synthesize across sources rather than listing what each one said individually.\n"
        "Use specific facts and figures from the summaries, not vague generalities.\n"
        "Do not include a Sources section as that is handled separately.\n"
    )
