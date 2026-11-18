#!/usr/bin/env python3
"""Reports whether this Mac is ready for a benchmark and which processes to stop. It never stops anything."""
import json
import os
import re
import subprocess
import sys
import time

MAX_IDLE_GPU_PERCENT = 15
MAX_OTHER_CPU_PERCENT = 150
MIN_FREE_MEMORY_PERCENT = 30
REPORT_CPU_PERCENT = 10
SYSTEM = {"kernel_task", "WindowServer", "launchd", "top", "ps", "logd", "mds", "mds_stores", "mdworker", "mdworker_shared",
          "coreaudiod", "cfprefsd", "distnoted", "powerd", "corespotlightd", "fseventsd", "syslogd", "ioreg", "sysmond"}


def output(*command):
    return subprocess.run(command, capture_output=True, text=True, errors="replace", check=False).stdout


def gpu_percent():
    samples = []
    for _ in range(5):
        found = re.search(r'"Device Utilization %"=(\d+)', output("ioreg", "-r", "-d", "1", "-c", "IOAccelerator"))
        samples.append(int(found.group(1)) if found else 0)
        time.sleep(1)
    return sum(samples) / len(samples)


def ancestors():
    known = set()
    pid = os.getpid()
    while pid > 1 and pid not in known:
        known.add(pid)
        parent = output("ps", "-o", "ppid=", "-p", str(pid)).strip()
        pid = int(parent) if parent else 1
    return known


def app_name(pid, fallback):
    path = output("ps", "-o", "comm=", "-p", str(pid)).strip() or fallback
    bundle = re.search(r"([^/]+)\.app/", path)
    return bundle.group(1) if bundle else os.path.basename(path)


def gpu_clients():
    text = output("ioreg", "-l", "-w0", "-c", "AGXDeviceUserClient")
    return {int(pid) for pid in re.findall(r'"IOUserClientCreator" = "pid (\d+),', text)}


def busy_apps():
    sample = output("top", "-l", "2", "-s", "2", "-n", "40", "-o", "cpu", "-stats", "pid,cpu,command")
    rows = sample[sample.rfind("PID"):].splitlines()[1:]
    own = ancestors()
    clients = gpu_clients()
    apps = {}
    for row in rows:
        parts = row.split(None, 2)
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        pid, cpu = int(parts[0]), float(parts[1].rstrip("*"))
        name = app_name(pid, parts[2].strip())
        if pid in own or name in SYSTEM:
            continue
        entry = apps.setdefault(name, {"name": name, "cpu_percent": 0.0, "uses_gpu": False, "pids": []})
        entry["cpu_percent"] = round(entry["cpu_percent"] + cpu, 1)
        entry["uses_gpu"] = entry["uses_gpu"] or pid in clients
        entry["pids"].append(pid)
    return sorted(apps.values(), key=lambda item: -item["cpu_percent"])


def inspect(max_other_cpu=MAX_OTHER_CPU_PERCENT):
    settings = output("pmset", "-g")
    power_mode = re.search(r"powermode\s+(\d)", settings)
    free = re.search(r"free percentage: (\d+)%", output("memory_pressure"))
    apps = busy_apps()
    state = {
        "on_ac_power": "AC Power" in output("pmset", "-g", "batt"),
        "power_mode": int(power_mode.group(1)) if power_mode else None,
        "thermal_warning": "No thermal warning" not in output("pmset", "-g", "therm"),
        "gpu_percent": round(gpu_percent(), 1),
        "other_cpu_percent": round(sum(item["cpu_percent"] for item in apps), 1),
        "free_memory_percent": int(free.group(1)) if free else None,
        "apps": [item for item in apps if item["cpu_percent"] >= REPORT_CPU_PERCENT or item["uses_gpu"]],
    }
    problems = []
    if not state["on_ac_power"]:
        problems.append("connect the power adapter")
    if state["power_mode"] != 2:
        problems.append("set Energy Mode to High Power in System Settings > Battery")
    if state["thermal_warning"]:
        problems.append("let the Mac cool down")
    if state["gpu_percent"] > MAX_IDLE_GPU_PERCENT:
        problems.append(f"the GPU is {state['gpu_percent']}% busy while idle (limit {MAX_IDLE_GPU_PERCENT}%)")
    if state["other_cpu_percent"] > max_other_cpu:
        problems.append(f"other apps use {state['other_cpu_percent']}% CPU (limit {max_other_cpu}%)")
    if state["free_memory_percent"] is not None and state["free_memory_percent"] < MIN_FREE_MEMORY_PERCENT:
        problems.append(f"only {state['free_memory_percent']}% of memory is free (limit {MIN_FREE_MEMORY_PERCENT}%)")
    state["max_other_cpu_percent"] = max_other_cpu
    state["problems"] = problems
    state["ready"] = not problems
    return state


def main():
    state = inspect()
    if "--json" in sys.argv:
        print(json.dumps(state, indent=2))
        return 0 if state["ready"] else 1
    print(f"power adapter: {state['on_ac_power']}  energy mode: {state['power_mode']} (2 is High Power)")
    print(f"idle GPU: {state['gpu_percent']}%  other apps CPU: {state['other_cpu_percent']}%  free memory: {state['free_memory_percent']}%")
    print("apps to consider stopping, busiest first:")
    for item in state["apps"]:
        print(f"  {item['name']}: CPU {item['cpu_percent']}%{'  uses GPU' if item['uses_gpu'] else ''}")
    for problem in state["problems"]:
        print(f"not ready: {problem}")
    print("verdict: " + ("ready" if state["ready"] else "not ready"))
    return 0 if state["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
