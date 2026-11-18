#!/usr/bin/env python3
"""Measures kizukani and other Apple Silicon engines on the same prompts, and writes the results to bench/results."""
import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

import preflight  # noqa: E402

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
PROMPTS = BENCH / "prompts"
WORK = BENCH / ".work"
MODELS = Path(os.environ.get("BENCH_MODELS", BENCH / "models"))
MLX_PYTHON = BENCH / "envs/mlx/.venv/bin/python"
OMLX_PYTHON = BENCH / "envs/omlx/.venv/bin/python"
TASKS = ["prose_short", "code_short", "thinking_short", "prose_long", "code_long", "thinking_long"]
WARMUP_TASK = "warmup"
CALIBRATION_TASK = "code_short"
CALIBRATION_TOKENS = 128
READY_CHECKS = 2
MAX_CALIBRATIONS = 3
CHECK_INTERVAL_SECONDS = 120


def json_lines(command, cwd=ROOT):
    result = subprocess.run([str(item) for item in command], cwd=cwd, capture_output=True, text=True, errors="replace", check=False)
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    if result.returncode != 0:
        raise RuntimeError(f"{command[0]} failed: {result.stderr[-1500:]}")
    return rows


def kizukani(model):
    def run(tasks, count):
        rows = []
        for task in tasks:
            command = ["target/kizukani", "gpu-speculative-selfcheck", "both", str(count), str(PROMPTS / f"{task}.ids"), model]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
            lines = [line.strip() for line in result.stdout.splitlines()]
            value = lambda label: int(lines[lines.index(label) + 1])
            summary = lines.index("matched of expected, generated, passes, milliseconds per generated token:")
            rows.append({
                "task": task, "prompt_tokens": len((PROMPTS / f"{task}.ids").read_text().split()), "generated": int(lines[summary + 2]),
                "prefill_s": value("prefill milliseconds:") / 1000, "decode_s": value("generation milliseconds:") / 1000,
            })
        return rows
    return run


def mlx(mode):
    def run(tasks, count):
        command = [MLX_PYTHON, BENCH / "drivers/mlx_driver.py", mode, MODELS / "mlx-4bit", MODELS / "mlx-mtp-4bit", PROMPTS, count, *tasks]
        return json_lines(command)
    return run


def omlx(tasks, count):
    command = [OMLX_PYTHON, BENCH / "drivers/omlx_driver.py", MODELS / "mlx-4bit", MODELS / "dflash2", WORK / "omlx", PROMPTS, count, *tasks]
    return json_lines(command)


def llama(tasks, count):
    return json_lines([sys.executable, BENCH / "drivers/llama_driver.py", MODELS / "gguf/Qwen3.8-27B-UD-Q4_K_M.gguf", PROMPTS, count, *tasks])


def mackani(tasks, count):
    return json_lines([WORK / "mackani-driver", ROOT / "models/qwen38-27b-speed", PROMPTS, count, *tasks])


ENGINES = {
    "kizukani-speed": kizukani("speed"),
    "kizukani-quality": kizukani("quality"),
    "mlx-4bit": mlx("plain"),
    "mlx-4bit-mtp": mlx("mtp"),
    "omlx-4bit-dflash2": omlx,
    "llama.cpp-q4": llama,
    "mackani-speed": mackani,
}


def with_rate(row):
    row["tok_s"] = round((row["generated"] - 1) / row["decode_s"], 2) if row["decode_s"] > 0 and row["generated"] > 1 else 0.0
    row["prefill_tok_s"] = round(row["prompt_tokens"] / row["prefill_s"], 1) if row["prefill_s"] > 0 else 0.0
    return row


def summary(results, tasks):
    lines = ["| Engine | " + " | ".join(tasks) + " |", "|---|" + "---|" * len(tasks)]
    for engine in dict.fromkeys(row["engine"] for row in results):
        cells = []
        for task in tasks:
            rates = [row["tok_s"] for row in results if row["engine"] == engine and row["task"] == task]
            cells.append(f"{statistics.mean(rates):.1f}" if rates else "-")
        lines.append(f"| {engine} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def wait_until_ready(wait_hours, min_calibration, max_other_cpu):
    """Returns the machine state once it is idle and plain MLX reaches min_calibration, or None at the deadline."""
    deadline = time.time() + wait_hours * 3600
    ready_checks = 0
    calibrations = 0
    while True:
        state = preflight.inspect(max_other_cpu)
        ready_checks = ready_checks + 1 if state["ready"] else 0
        print(time.strftime("%H:%M:%S"), "ready" if state["ready"] else "waiting: " + "; ".join(state["problems"]), flush=True)
        if ready_checks >= READY_CHECKS:
            rate = with_rate(ENGINES["mlx-4bit"]([CALIBRATION_TASK], CALIBRATION_TOKENS)[0])["tok_s"]
            print(f"calibration: plain MLX {rate} tok/s", flush=True)
            if rate >= min_calibration:
                return state
            calibrations += 1
            if calibrations >= MAX_CALIBRATIONS:
                print(f"plain MLX stayed below {min_calibration} tok/s in {MAX_CALIBRATIONS} calibrations", flush=True)
                return None
            ready_checks = 0
        if time.time() >= deadline:
            return None
        time.sleep(CHECK_INTERVAL_SECONDS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engines", default=",".join(ENGINES))
    parser.add_argument("--tasks", default=",".join(TASKS))
    parser.add_argument("--count", type=int, default=256)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--min-calibration", type=float, default=25.0, help="tok/s that plain MLX must reach before the run")
    parser.add_argument("--max-other-cpu", type=float, default=preflight.MAX_OTHER_CPU_PERCENT, help="CPU percent that other apps may use")
    parser.add_argument("--wait-hours", type=float, default=0.0, help="keep checking for this long until the Mac is idle, then measure")
    parser.add_argument("--force", action="store_true", help="measure now without the readiness and calibration gates")
    parser.add_argument("--smoke", action="store_true", help="check that every engine runs; skips the readiness gates and saves nothing")
    arguments = parser.parse_args()
    engines = arguments.engines.split(",")
    tasks = arguments.tasks.split(",")
    state = preflight.inspect()
    if not arguments.smoke and not arguments.force:
        state = wait_until_ready(arguments.wait_hours, arguments.min_calibration, arguments.max_other_cpu)
        if state is None:
            print("the Mac did not become ready, so nothing was measured", file=sys.stderr)
            return 3
    results = []
    for round_index in range(arguments.rounds):
        for engine in engines:
            for row in ENGINES[engine]([WARMUP_TASK, *tasks], arguments.count)[1:]:
                row = with_rate({"engine": engine, "round": round_index + 1, **row})
                results.append(row)
                print(json.dumps(row), flush=True)
    print(summary(results, tasks))
    if not arguments.smoke:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        state = {key: value for key, value in state.items() if key != "apps"}
        record = {"conditions": {"chip": chip, "macos": platform.mac_ver()[0], "count": arguments.count, "gated": not arguments.force, "preflight": state}, "results": results}
        (BENCH / "results" / f"{stamp}.json").write_text(json.dumps(record, indent=2) + "\n")
        (BENCH / "results" / f"{stamp}.md").write_text(summary(results, tasks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
