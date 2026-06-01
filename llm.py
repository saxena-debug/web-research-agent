'''Creating this which is the central LLM wrapper:all calls go through here so swapping the provider
only requires editing this one file'''

import json
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

def call_llm(system: str, user: str, temperature: float = 0.3) -> tuple:

    '''I am keeping temp 0.3 is low enough to be consistent, not 0 so it doesn't
    sounding completely robotic in the compiled report '''


    response = client.chat.completions.create(
        model=config.MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
    )
    tokens = response.usage.total_tokens if response.usage else 0
    return response.choices[0].message.content.strip(), tokens


def call_llm_json(system: str, user: str, temperature: float = 0) -> tuple:
    '''sometimes the model returns empty string or wraps  json in markdown code fences
    like 'json..' so I will  strip those before parsing. if parsing still fails I return
    empty dict rather than crashing, callers check for missing keys anyways'''
    content, tokens = call_llm(system, user, temperature=temperature)
    clean = content.strip("```json").strip("```").strip()
    if not clean:
        return {}, tokens
    try:
        return json.loads(clean), tokens
    except json.JSONDecodeError:
        return {}, tokens
