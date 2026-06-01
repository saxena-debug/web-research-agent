import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
import config
from prompts import expand_queries_prompt, grade_results_prompt


# config sanity checks
# I  just making sure the yaml loaded correctly and the keys are actually there

def test_config_model_is_set():
    assert isinstance(config.MODEL, str) and len(config.MODEL) > 0

def test_config_threshold_is_valid():
    assert 0.0 < config.QUALITY_THRESHOLD <= 1.0

def test_config_api_keys_present():
    assert config.OPENAI_API_KEY and config.TAVILY_API_KEY


# grader threshold logic
# the whole retry loop depends on this being correct

def _resp(score):
    return ({"score": score, "issues": "x", "missing_topics": "y", "query_suggestions": "z"}, 50)

def test_grader_passes_above_threshold():
    with patch("metrics.call_llm_json", return_value=_resp(0.8)):
        from metrics import grade_results
        passed, score, _, _ = grade_results("goal", "results", threshold=0.6)
        assert passed is True and score == 0.8

def test_grader_fails_below_threshold():
    with patch("metrics.call_llm_json", return_value=_resp(0.4)):
        from metrics import grade_results
        passed, _, _, _ = grade_results("goal", "results", threshold=0.6)
        assert passed is False

def test_grader_passes_exactly_at_threshold():
    with patch("metrics.call_llm_json", return_value=_resp(0.6)):
        from metrics import grade_results
        passed, _, _, _ = grade_results("goal", "results", threshold=0.6)
        assert passed is True


# prompt content checks
# if these break something changed in how prompts are built

def test_prompt_contains_goal():
    assert "find laptops" in expand_queries_prompt("find laptops")

def test_prompt_uses_config_query_count():
    assert "Generate " + str(config.MAX_QUERIES) in expand_queries_prompt("goal")

def test_prompt_threshold_flows_through():
    assert "0.75" in grade_results_prompt("goal", "results", threshold=0.75)
