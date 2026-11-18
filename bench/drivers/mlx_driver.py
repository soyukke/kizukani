#!/usr/bin/env python3
"""Runs MLX without speculation (mlx-lm) or with the MTP drafter (mlx-vlm) and prints one JSON line per task."""
import json
import sys
import time


def measure(stream, task, prompt_tokens):
    started = time.perf_counter()
    first = None
    last = None
    for last in stream:
        first = first or time.perf_counter()
    finished = time.perf_counter()
    print(json.dumps({
        "task": task, "prompt_tokens": prompt_tokens, "generated": last.generation_tokens,
        "prefill_s": round(first - started, 3), "decode_s": round(finished - first, 3),
    }), flush=True)


def main():
    mode, model_dir, draft_dir, tasks_dir, count = sys.argv[1:6]
    names = sys.argv[6:]
    count = int(count)
    if mode == "plain":
        from mlx_lm import load, stream_generate

        model, tokenizer = load(model_dir)
        for name in names:
            ids = [int(item) for item in open(f"{tasks_dir}/{name}.ids").read().split()]
            measure(stream_generate(model, tokenizer, ids, max_tokens=count), name, len(ids))
        return
    from mlx_vlm import load, stream_generate
    from mlx_vlm.speculative.drafters import load_drafter

    model, processor = load(model_dir)
    drafter, kind = load_drafter(draft_dir)
    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    for name in names:
        ids = [int(item) for item in open(f"{tasks_dir}/{name}.ids").read().split()]
        text = tokenizer.decode(ids, skip_special_tokens=False)
        stream = stream_generate(model, processor, text, max_tokens=count, temperature=0.0, draft_model=drafter, draft_kind=kind)
        measure(stream, name, len(ids))


main()
