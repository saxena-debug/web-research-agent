import json
from tavily import TavilyClient
import config
from llm import call_llm_json, call_llm
from prompts import expand_queries_prompt, summarize_source_prompt

tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)


def expand_queries(goal, feedback=""):
    return call_llm_json(
        system="You generate search queries. Return only valid JSON.",
        user=expand_queries_prompt(goal, feedback),
        temperature=0.6,
    )


def tavily_search(queries):
    # fetch from tavily, dedup by url — doesnt preserve original ranking but thats fine
    all_results = []
    all_images  = []
    seen_urls   = set()
    seen_images = set()

    for query in queries:
        response = tavily_client.search(
            query,
            max_results=config.MAX_SEARCH_RESULTS,
            include_images=True,
            include_favicon=True,
            include_raw_content=True,
            exclude_domains=config.BLOCKLIST,
        )
        for r in response.get("results", []):
            if r.get("url") not in seen_urls:
                seen_urls.add(r.get("url"))
                all_results.append(r)

        for img in response.get("images", []):
            if img and img not in seen_images:
                seen_images.add(img)
                all_images.append(img)

    return all_results, all_images[:12]


def summarize_sources(goal, results):
    total_tokens = 0
    summaries    = []
    dropped      = []

    cap     = config.MAX_SUMMARIZE_SOURCES  # configurable, default 5
    skipped = results[cap:]

    # TODO: maybe I should cache tavily results across retries so when quality fails, i use this
    # re-fetch the same URLs by just rewriting the queries and merge new results!!

    for r in results[:cap]:
        title   = r.get("title", "")
        url     = r.get("url", "")
        favicon = r.get("favicon", "")

        # full raw_content
        # because the reports were too shallow before
        content = r.get("raw_content") or r.get("content", "")
        if not content:
            dropped.append({"title": title, "url": url, "reason": "no content returned"})
            continue

        # char limit is configurable via config.yaml — higher = richer summaries but more tokens
        content = content[:config.SOURCE_CHAR_LIMIT]

        # print(title, len(content))
        summary_text, tokens = call_llm(
            system="You extract relevant research information from web pages. Be concise and specific.",
            user=summarize_source_prompt(goal, title, content),
            temperature=0,
        )
        total_tokens += tokens

        if summary_text.lower() == "not relevant.":
            dropped.append({"title": title, "url": url, "reason": "not relevant to goal"})
        else:
            summaries.append({
                "title":   title,
                "url":     url,
                "favicon": favicon,
                "summary": summary_text,
            })

    formatted = "\n\n".join(
        "[" + str(i+1) + "] " + s["title"] + " (" + s["url"] + ")\n" + s["summary"]
        for i, s in enumerate(summaries)
    )

    for r in skipped:
        dropped.append({
            "title":  r.get("title", ""),
            "url":    r.get("url", ""),
            "reason": "skipped — over processing cap",
        })

    return summaries, formatted, dropped, total_tokens


def format_results_for_prompt(results):
    '''Fallback shallow formatter — only used if summarize_sources is skipped.'''
    top = results[:10]
    return "\n".join(
        "- " + r.get("title", "") + ": " + r.get("content", "")[:1000] + " (" + r.get("url", "") + ")"
        for r in top
    )
