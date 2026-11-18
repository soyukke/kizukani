#!/usr/bin/env python3
"""Writes the benchmark prompts as token ids, using the model's own tokenizer and chat template."""
import json
import sys
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LONG_DOCUMENT_TOKENS = 2000

SHORT = {
    "warmup": ("List ten colors and describe each one in a sentence.", False),
    "prose_short": ("Write a long, detailed essay about how lighthouses guided ships before electronic navigation.", False),
    "code_short": ("Write a complete Python implementation of an LRU cache with a thread-safe wrapper and unit tests.", False),
    "thinking_short": ("A tank fills through two pipes in 6 and 9 hours and drains through a third in 12 hours. How long does it take to fill with all three open? Check the result in two ways.", True),
}
LONG = {
    "prose_long": ("LICENSE", "Summarize every section of the license above in detail, in plain language.", False),
    "code_long": ("src/text/tokenizer.kizu", "Explain how the code above works, function by function, then propose unit tests for it.", False),
    "thinking_long": ("src/model/draft.kizu", "Review the code above carefully and describe the invariants it depends on.", True),
}


def encode(tokenizer, message, thinking):
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": message}], tokenize=False, add_generation_prompt=True, enable_thinking=thinking
    )
    return tokenizer.encode(text, add_special_tokens=False)


def main():
    tokenizer = AutoTokenizer.from_pretrained(sys.argv[1])
    manifest = {}
    tasks = {name: (message, thinking) for name, (message, thinking) in SHORT.items()}
    for name, (path, request, thinking) in LONG.items():
        document = tokenizer.encode((ROOT / path).read_text(), add_special_tokens=False)[:LONG_DOCUMENT_TOKENS]
        tasks[name] = (tokenizer.decode(document) + "\n\n" + request, thinking)
    for name, (message, thinking) in tasks.items():
        ids = encode(tokenizer, message, thinking)
        (OUT / f"{name}.ids").write_text(" ".join(str(item) for item in ids) + "\n")
        manifest[name] = {"prompt_tokens": len(ids), "thinking": thinking}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


main()
