#!/usr/bin/env python3
"""Runs oMLX with the DFlash 2 drafter on loopback and prints one JSON line per task."""
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from transformers import AutoTokenizer

PORT = 18473
KEY = "local-bench"
MODEL_ID = "Qwen3.8-27B-4bit"


def request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"}
    return urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, headers=headers), timeout=900)


def wait_for_server():
    for _ in range(180):
        try:
            if MODEL_ID in request("/v1/models").read().decode():
                return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError("the oMLX server did not start")


def run_task(tokenizer, tasks_dir, name, count):
    ids = [int(item) for item in open(f"{tasks_dir}/{name}.ids").read().split()]
    body = {
        "model": MODEL_ID, "prompt": tokenizer.decode(ids, skip_special_tokens=False), "max_tokens": count,
        "temperature": 0.0, "stream": True, "stream_options": {"include_usage": True},
    }
    started = time.perf_counter()
    first = last = None
    usage = {}
    with request("/v1/completions", body) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            event = json.loads(line[6:])
            usage = event.get("usage") or usage
            if any(choice.get("text") for choice in event.get("choices", [])):
                last = time.perf_counter()
                first = first or last
    print(json.dumps({
        "task": name, "prompt_tokens": len(ids), "generated": usage.get("completion_tokens", 0),
        "prefill_s": round(first - started, 3), "decode_s": round(last - first, 3),
    }), flush=True)


def main():
    model_dir, draft_dir, work_dir, tasks_dir, count = sys.argv[1:6]
    work = Path(work_dir)
    shutil.rmtree(work, ignore_errors=True)
    (work / "base").mkdir(parents=True)
    (work / "models").mkdir()
    (work / "models" / MODEL_ID).symlink_to(Path(model_dir).resolve())
    settings = {"version": 1, "models": {MODEL_ID: {"dflash_enabled": True, "dflash_draft_model": str(Path(draft_dir).resolve())}}}
    (work / "base" / "model_settings.json").write_text(json.dumps(settings))
    server = subprocess.Popen(
        [str(Path(sys.executable).with_name("omlx")), "serve", "--base-path", str(work / "base"), "--model-dir", str(work / "models"),
         "--host", "127.0.0.1", "--port", str(PORT), "--api-key", KEY],
        stdout=open(work / "server.log", "w"), stderr=subprocess.STDOUT,
    )
    try:
        wait_for_server()
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        for name in sys.argv[6:]:
            run_task(tokenizer, tasks_dir, name, int(count))
    finally:
        server.terminate()
        server.wait(timeout=60)


main()
