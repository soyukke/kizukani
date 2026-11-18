#!/usr/bin/env python3
"""Runs llama.cpp on Metal on loopback and prints one JSON line per task."""
import json
import subprocess
import sys
import time
import urllib.request

PORT = 18474


def main():
    model, tasks_dir, count = sys.argv[1:4]
    server = subprocess.Popen(
        ["llama-server", "-m", model, "--host", "127.0.0.1", "--port", str(PORT), "-ngl", "999", "-c", "8192", "-np", "1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(300):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2).read()
                break
            except OSError:
                time.sleep(1)
        for name in sys.argv[4:]:
            ids = [int(item) for item in open(f"{tasks_dir}/{name}.ids").read().split()]
            body = {"prompt": ids, "n_predict": int(count), "temperature": 0.0, "ignore_eos": True, "cache_prompt": False, "stream": False}
            request = urllib.request.Request(f"http://127.0.0.1:{PORT}/completion", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            timings = json.load(urllib.request.urlopen(request, timeout=1800))["timings"]
            print(json.dumps({
                "task": name, "prompt_tokens": len(ids), "generated": timings["predicted_n"],
                "prefill_s": round(timings["prompt_ms"] / 1000, 3), "decode_s": round(timings["predicted_ms"] / 1000, 3),
            }), flush=True)
    finally:
        server.terminate()
        server.wait(timeout=60)


main()
