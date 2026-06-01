import config
from llm import call_llm_json
from prompts import grade_results_prompt


def grade_results(goal, formatted_results, threshold=None):
    # deliberately lenient grader — see grade_results_prompt for the exact rules.
    # earlier version was too strict and kept retrying on perfectly fine results
    # just because a source used USD prices instead of EUR.
    cutoff = threshold if threshold is not None else config.QUALITY_THRESHOLD

    result, tokens = call_llm_json(
        system="You are an evaluator. Return only valid JSON.",
        user=grade_results_prompt(goal, formatted_results, threshold=cutoff),
        temperature=0,
    )

    score  = result.get("score", 0)
    passed = score >= cutoff

    # structured feedback — each field targets a specific part of the retry prompt
    feedback = {
        "issues":           result.get("issues", ""),
        "missing_topics":   result.get("missing_topics", ""),
        "query_suggestions": result.get("query_suggestions", ""),
    }

    return passed, score, feedback, tokens
