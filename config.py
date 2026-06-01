import os
import yaml
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY missing. Check your .env file.")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY missing. Check your .env file.")

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)

MODEL                 = _cfg["model"]
MAX_RETRIES           = _cfg["agent"]["max_retries"]
MAX_SEARCH_RESULTS    = _cfg["agent"]["max_search_results"]
MAX_QUERIES           = _cfg["agent"]["max_queries"]
MAX_SUMMARIZE_SOURCES = _cfg["agent"]["max_summarize_sources"]

SOURCE_CHAR_LIMIT        = _cfg["depth"]["source_char_limit"]
SOURCE_SUMMARY_SENTENCES = _cfg["depth"]["source_summary_sentences"]
EXEC_SUMMARY_SENTENCES   = _cfg["depth"]["exec_summary_sentences"]
ANALYSIS_PARAGRAPHS      = _cfg["depth"]["analysis_paragraphs"]

QUALITY_THRESHOLD     = _cfg["thresholds"]["quality"]
BLOCKLIST             = _cfg["trust_filter"]["blocklist"]
LOG_DIR               = _cfg["logging"]["log_dir"]
REPORT_DIR            = _cfg["logging"]["report_dir"]
