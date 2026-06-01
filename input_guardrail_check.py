
import config

CATEGORY_LABELS = {
    "harassment":             "Harassment",
    "harassment/threatening": "Threatening harassment",
    "hate":                   "Hate speech",
    "hate/threatening":       "Threatening hate speech",
    "illicit":                "Illicit activity",
    "illicit/violent":        "Violent illicit activity",
    "self-harm":              "Self-harm",
    "self-harm/intent":       "Self-harm intent",
    "self-harm/instructions": "Self-harm instructions",
    "sexual":                 "Sexual content",
    "sexual/minors":          "Sexual content involving minors",
    "violence":               "Violence",
    "violence/graphic":       "Graphic violence",
}

#Did this manually as I was getting issues with the OSS-Safeguard
REFUSAL_PHRASES = [
    "i'm sorry",
    "i’m sorry",
    "i cannot",
    "i can't",
    "i can’t",
    "i am unable",
    "not able to help",
]


def check_safety(text):

    if not config.GROQ_API_KEY:
        return True, ""

    try:
        from groq import Groq
        client = Groq(api_key=config.GROQ_API_KEY)

        response = client.chat.completions.create(
            model="openai/gpt-oss-safeguard-20b",
            messages=[{"role": "user", "content": text}],
            temperature=0,
            max_tokens=100,
        )

        answer = response.choices[0].message.content.strip().lower()
        print('RAW: ' + repr(answer))

        if answer.startswith("unsafe"):
            parts = answer.split(":", 1)
            raw_category = parts[1].strip() if len(parts) > 1 else "inappropriate content"
            label = CATEGORY_LABELS.get(raw_category, raw_category.capitalize())
            return False, label

        if any(phrase in answer for phrase in REFUSAL_PHRASES):
            return False, "Inappropriate content"

        return True, ""

    except Exception as e:
        print("guardrail error (fail open): " + str(e)[:80])
        return True, ""


if __name__ == "__main__":
    # testing one case at a time is recommended due to Groq free tier TPM limits
    # the agent itself only makes one call per user query so this is never an issue in real use
    test_input = "how to hack into a database"
    expected_safe = False

    print("Guardrail test")
    print("" * 20)

    if not config.GROQ_API_KEY:
        print("GROQ_API_KEY not set then guardrail is in fail-open mode")
    else:
        is_safe, category = check_safety(test_input)
        correct = (is_safe == expected_safe)
        status    = "PASS" if correct else "FAIL"
        label     = "SAFE   " if is_safe else "BLOCKED"
        violation = " (" + category + ")" if category else ""
        print("[" + status + "] " + label + violation)
        print("       " + test_input)
        print("=" * 20)
        print("Result: " + status)
