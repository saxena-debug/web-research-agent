import time
import uuid
import re as _re

import config
from llm import call_llm, call_llm_json
from tools import expand_queries, tavily_search, summarize_sources, format_results_for_prompt
from metrics import grade_results
from logger import AgentLogger
from prompts import plan_prompt, compile_prompt
from input_guardrail_check import check_safety


def _strip_sources_section(text):
    pattern = _re.compile(
        r'\n{0,2}(#{1,3}\s*)?(sources|references|bibliography)(\s*\n.*)?$',
        _re.IGNORECASE | _re.DOTALL,
    )
    return pattern.sub("", text).rstrip()


class ResearchAgent:
    def __init__(self):
        self.run_id = str(uuid.uuid4())[:8]
        self.logger = AgentLogger(self.run_id)

    def plan(self, goal):
        content, tokens = call_llm_json(
            system="You create research plans. Return only valid JSON.",
            user=plan_prompt(goal),
        )
        self.logger.log_llm_trace("plan", plan_prompt(goal), str(content), tokens=tokens)
        return content, tokens

    def run(self, goal, quality_threshold=None, callback=None):
        threshold = quality_threshold if quality_threshold is not None else config.QUALITY_THRESHOLD

        def update(msg, status="running", score=None):
            if callback:
                callback({"msg": msg, "status": status, "score": score})

        self.logger.log_run_start(goal)

        # guardrail check r
        is_safe, violation = check_safety(goal)
        if not is_safe:
            update("Query flagged by safety check: " + violation, "blocked")
            self.logger.log_task("guardrail", "blocked", reason=violation)
            self.logger.log_run_end("blocked")
            self.logger.log_blocked(violation)
            return {
                "run_id":        self.run_id,
                "goal":          goal,
                "blocked":       True,
                "violation":     violation,
                "report":        "This query was flagged as inappropriate and was not processed.\n\nViolation category: " + violation,
                "total_tokens":  0,
                "quality_score": 0,
                "sources":       [],
                "images":        [],
                "total_time":    0,
            }

        start_total = time.time()
        total_tokens = 0
        token_breakdown = {
            "plan":              0,
            "query_expansion":   0,
            "summarize_sources": 0,
            "quality_check":     0,
            "compile":           0,
        }

        update("Creating research plan...")
        tasks, tokens = self.plan(goal)
        total_tokens += tokens
        token_breakdown["plan"] += tokens
        update("Plan ready — " + str(len(tasks)) + " tasks", "done")

        '''I have a pipeline which is hardcoded regardless of what the planner returns. ideally each task
        in the plan would trigger a focused sub-search'''

        update("Expanding search queries...")
        t = time.time()
        queries, tokens = expand_queries(goal)
        total_tokens += tokens
        token_breakdown["query_expansion"] += tokens
        self.logger.log_task("query_expansion", "done", duration_ms=int((time.time()-t)*1000))
        update("Generated " + str(len(queries)) + " queries", "done")

        update("Searching the web...")
        t = time.time()
        results, images = tavily_search(queries)
        self.logger.log_task("web_search", "done", duration_ms=int((time.time()-t)*1000))
        update("Found " + str(len(results)) + " results, " + str(len(images)) + " images", "done")

        update("Reading and summarizing sources...")
        t = time.time()
        summaries, formatted, dropped, tokens = summarize_sources(goal, results)
        total_tokens += tokens
        token_breakdown["summarize_sources"] += tokens
        self.logger.log_task("summarize_sources", "done", duration_ms=int((time.time()-t)*1000))
        for d in dropped:
            self.logger.log_task("source_dropped", "dropped",
                                 reason=d["reason"], score=d["url"])
        update("Summarized " + str(len(summaries)) + " sources (" + str(len(dropped)) + " dropped)", "done")

        '''This is a retry loop : feedback from grader feeds back into query expansion
        TOFIX: this re-runs the full search + summarize from scratch on retry,
        which means were throwing away valid summaries just because a few sources were bad.
        a smarter approach would cache the good ones and only refetch the gaps.'''

        quality_score, feedback = 0.0, {}
        for attempt in range(config.MAX_RETRIES + 1):
            update("Grading results (attempt " + str(attempt+1) + ")...")
            t = time.time()
            passed, quality_score, feedback, tokens = grade_results(goal, formatted, threshold=threshold)
            total_tokens += tokens
            token_breakdown["quality_check"] += tokens
            duration = int((time.time()-t)*1000)
            self.logger.log_task(
                "quality_check",
                "done" if passed else "retry",
                score=quality_score,
                reason=str(feedback),
                duration_ms=duration,
            )
            if passed:
                update("Quality check passed — " + "%.2f" % quality_score, "done", score=quality_score)
                break
            update(
                "Quality low (" + "%.2f" % quality_score + ") — refining queries based on feedback...",
                "retry",
                score=quality_score,
            )
            if attempt < config.MAX_RETRIES:
                queries, tokens = expand_queries(goal, feedback=feedback)
                total_tokens += tokens
                token_breakdown["query_expansion"] += tokens
                results, images = tavily_search(queries)
                summaries, formatted, dropped, tokens = summarize_sources(goal, results)
                total_tokens += tokens
                token_breakdown["summarize_sources"] += tokens
                for d in dropped:
                    self.logger.log_task("source_dropped", "dropped",
                                         reason=d["reason"], score=d["url"])

        # if quality never passed after all retries, show that to the user.
        if not passed:
            update("Quality threshold not met after all retries — skipping report", "retry", score=quality_score)
            self.logger.log_run_end("quality_failed", tokens_used=total_tokens)
            return {
                "run_id":          self.run_id,
                "goal":            goal,
                "report":          "The agent was unable to find sources good enough to write a reliable report for this goal.\n\nQuality score after " + str(config.MAX_RETRIES + 1) + " attempts: " + "%.2f" % quality_score + "\n\nTry rephrasing your goal or being more specific.",
                "token_breakdown": token_breakdown,
                "quality_score":   quality_score,
                "total_tokens":    total_tokens,
                "sources":         summaries,
                "images":          images,
                "total_time":      round(time.time() - start_total, 1),
                "low_quality":     True,
            }

        update("Compiling final report...")
        t = time.time()
        report_text, tokens = call_llm(
            system="You are a research analyst writing a thorough, insightful report.",
            user=compile_prompt(goal, formatted),
        )
        total_tokens += tokens
        token_breakdown["compile"] += tokens
        report_text = _strip_sources_section(report_text)
        self.logger.log_task("compile_report", "done", duration_ms=int((time.time()-t)*1000))
        self.logger.log_llm_trace("compile", compile_prompt(goal, formatted), report_text, tokens=tokens)
        update("Report ready", "done")

        total = round(time.time() - start_total, 1)
        self.logger.log_run_end("done", tokens_used=total_tokens)

        return {
            "run_id":          self.run_id,
            "goal":            goal,
            "report":          report_text,
            "token_breakdown": token_breakdown,
            "quality_score":   quality_score,
            "total_tokens":    total_tokens,
            "sources":         summaries,
            "images":          images,
            "total_time":      total,
        }
